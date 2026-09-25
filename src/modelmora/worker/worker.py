"""The single generation worker (T032, R-4): one thread, one generation at a time.

Owns the moment a queued request becomes `running`: it asks `queue.ordering` which
waiting request to run next, brings its model onto the GPU through `Residency`
(loading and evicting exactly as `worker/residency.py` already decides), runs the
generation, and reports what happened through the callbacks it was built with. Because
exactly one worker exists and it finishes one request before starting the next,
`Residency.ensure_loaded` is never called concurrently -- closing the race
`api/requests.py` used to document as this task's job. A model whose declared
footprint alone cannot fit is refused before queueing (`api/validate.py`), so
`ensure_loaded` raising here would be a defect, not an expected path.

Idle-unload (`Residency.unload_idle`) is checked every time the worker finds nothing
waiting, so a Studio that goes quiet for the idle timeout frees its GPU without a
caller ever having to ask.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from modelmora.queue.estimates import Estimator
from modelmora.queue.line import Line, QueuedRequest
from modelmora.queue.ordering import pick_next
from modelmora.refusals import ModelMoraRefusal
from modelmora.runners.base import GeneratedImage, GeneratedText
from modelmora.worker.residency import Residency

# Short enough that stopping the worker or noticing an idle GPU never takes long;
# long enough not to spin. `idle_unload_seconds` is minutes, so this resolution is
# more than fine-grained enough to honor it.
_IDLE_CHECK_SECONDS = 0.1

OnRunning = Callable[[QueuedRequest], None]
OnDone = Callable[[QueuedRequest, "GeneratedText | GeneratedImage", float], None]
OnFailed = Callable[[QueuedRequest, BaseException], None]


class Worker:
    """Runs on its own thread; every public method here is safe to call from another."""

    def __init__(
        self,
        *,
        line: Line,
        residency_provider: Callable[[], Residency],
        estimator: Estimator,
        overtaking_seconds: float,
        idle_unload_seconds: float,
        on_running: OnRunning,
        on_done: OnDone,
        on_failed: OnFailed,
    ) -> None:
        self._line = line
        self._residency_provider = residency_provider
        self._estimator = estimator
        self._overtaking_seconds = overtaking_seconds
        self._idle_unload_seconds = idle_unload_seconds
        self._on_running = on_running
        self._on_done = on_done
        self._on_failed = on_failed
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="modelmora-worker", daemon=True)
        self._thread.start()

    def stop(self, *, timeout: float | None = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        # `residency` is read fresh inside `picker` and again just below, never cached
        # across the blocking wait: a test (or a future hot-swap) that reassigns
        # `state.residency` while the worker is idle must take effect on the very next
        # request, not on whichever residency existed when the wait began.
        def picker(waiting: list[QueuedRequest]) -> QueuedRequest:
            return pick_next(
                waiting, self._residency_provider().resident_keys(), self._overtaking_seconds
            )

        while not self._stop_event.is_set():
            request = self._line.wait_for_next(pick=picker, timeout=_IDLE_CHECK_SECONDS)
            if request is None:
                self._residency_provider().unload_idle(self._idle_unload_seconds)
                continue
            self._process(request, self._residency_provider())

    def _process(self, request: QueuedRequest, residency: Residency) -> None:
        self._on_running(request)
        started = time.monotonic()
        try:
            was_resident = request.runner.is_loaded()
            load_started = time.monotonic()
            residency.ensure_loaded(request.runner)
            if not was_resident:
                self._estimator.record_load(request.model, time.monotonic() - load_started)
            generated = request.generate()
        except ModelMoraRefusal as refusal:
            self._line.finish_running()
            self._on_failed(request, refusal)
            return
        except Exception as exc:  # the model backend failed unexpectedly (spec Edge Cases)
            self._line.finish_running()
            self._on_failed(request, exc)
            return
        self._estimator.record_generation(request.model, time.monotonic() - started)
        self._line.finish_running()
        self._on_done(request, generated, time.monotonic() - started)
