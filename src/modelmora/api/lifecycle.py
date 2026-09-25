"""The starting, running and stopping states (T046, FR-029, US5).

`Lifecycle` is nothing more than which of the three states ModelMora is in right now;
`api/availability.py` (T047) reads it to answer callers, and `api/requests.py` reads it
to refuse new work with an honest `starting` or `stopping` reason instead of a memory
error or a request that is accepted and then never runs (Edge Cases, US5 scenario 1).
`shutdown` is the other half: draining the line so nothing is left open (FR-014,
SC-009) when the process stops.
"""

from __future__ import annotations

import threading
import uuid
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from modelmora.api.state import AppState

LifecycleState = Literal["starting", "running", "stopping"]

# No configured startup or shutdown duration exists (plan.md names none), so this is a
# short, honest placeholder for "try again shortly" rather than a measured estimate --
# unlike `busy`, whose retry time comes from the estimator (queue/estimates.py).
LIFECYCLE_RETRY_AFTER_SECONDS = 5


class Lifecycle:
    """Starts `starting`, moves to `running` once ready, and to `stopping` on shutdown.

    There is no path back from `stopping`: once a Studio process is told to stop, it
    stops. A fresh `Lifecycle` (and thus a fresh process) is what "starting" again
    means.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: LifecycleState = "starting"

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def mark_ready(self) -> None:
        """`starting` -> `running`, once there is nothing left to prepare.

        A no-op once already `running` or `stopping`: `create_app` calls this
        unconditionally after starting the worker, and must never revive a process
        that is already on its way out.
        """
        with self._lock:
            if self._state == "starting":
                self._state = "running"

    def begin_stopping(self) -> None:
        with self._lock:
            self._state = "stopping"

    def refusal_reason(self) -> Literal["starting", "stopping"] | None:
        """`None` means new work may be admitted; otherwise the reason to refuse it."""
        state = self.state
        return state if state in ("starting", "stopping") else None


def shutdown(state: AppState) -> None:
    """Stops admitting new work and answers every request that was still open.

    `begin_stopping` runs first, so a submission racing this call is refused outright
    (`stopping`, never silently dropped) rather than slipping into the line behind our
    back. The waiting and currently-running requests already admitted are marked
    `stopped_before_completion` (US5 scenario 2, SC-009) *before* the worker thread is
    joined, so a caller polling right after this call returns sees that answer
    immediately -- it never depends on how long the join below takes. A running
    generation cannot be interrupted mid-flight, so its eventual
    `record_success`/`record_failure` becomes a no-op against the terminal state
    already recorded here (`RequestStore.mark_terminal_if_open`).

    The worker thread is still joined, with its own default timeout, rather than only
    signalled: on real GPU hardware, abandoning a thread mid-`torch`/`diffusers` call
    and letting interpreter shutdown tear it down anyway aborts the process (observed
    on the Studio, T049) -- worse for an operator than `shutdown` itself taking a
    little longer to return.

    Every resident runner is unloaded once the worker has stopped, not left for
    process exit to clean up: a runner that owns a subprocess of its own
    (`LlamaCppTextRunner`, spec 002 amendment) is not a child the OS tears down just
    because this process does, and letting it be a caller's own memory error
    unloading it would be exactly the failure FR-009 exists to prevent -- discovered
    on the Studio (T061) as an orphaned `llama-server` still holding the GPU after a
    clean shutdown.
    """
    state.lifecycle.begin_stopping()
    open_ids: list[uuid.UUID] = []
    if state.line is not None:
        open_ids.extend(state.line.drain_waiting())
        running_id = state.line.running_request_id()
        if running_id is not None:
            open_ids.append(running_id)
    for request_id in open_ids:
        state.store.mark_terminal_if_open(request_id, state="stopped_before_completion")
    if state.worker is not None:
        state.worker.stop()
    for runner in state.residency.resident_runners():
        runner.unload()
    state.holding.wipe()
