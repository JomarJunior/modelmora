"""The line: admission against the limit, and the single worker's handoff (T030).

`queue/ordering.py` decides only *which* waiting request the worker takes next; the
line itself is nothing more than "who is waiting, in what order they arrived, and who
is running now" (FR-015, FR-019). `RequestStore` (`api/requests.py`) holds the
caller-visible state and result once a request leaves here, whether by finishing,
failing or being withdrawn.
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from modelmora.messages import ModelKind, ModelRef
from modelmora.queue.estimates import Estimator
from modelmora.refusals import ModelMoraRefusal
from modelmora.runners.base import GeneratedImage, GeneratedText, Runner

Generate = Callable[[], "GeneratedImage | GeneratedText"]


@dataclass
class QueuedRequest:
    """One admitted request, as the worker needs to see it.

    `generate` is a closure over the request's own instructions or description and
    settings, built by `api/requests.py`; the worker calls it without knowing anything
    about text or images beyond `kind`.
    """

    request_id: uuid.UUID
    caller: str
    kind: ModelKind
    model: ModelRef
    runner: Runner
    submitted_at: datetime
    generate: Generate


@dataclass(frozen=True)
class LineStanding:
    """Where a request stands right now: 0 means running (matches the wire contract)."""

    position: int
    ahead_models: list[ModelRef]


class Line:
    """FIFO admission with a limit (FR-015); the worker is its one consumer."""

    def __init__(self, *, limit: int) -> None:
        self._limit = limit
        self._condition = threading.Condition()
        self._waiting: deque[QueuedRequest] = deque()
        self._running: QueuedRequest | None = None

    def submit(self, request: QueuedRequest, *, estimator: Estimator, resident: bool) -> None:
        """Admits `request`, or raises `busy` with an honest retry estimate (FR-015).

        The check and the append happen under the same lock, so two callers racing for
        the last slot cannot both be admitted (never accepted and then dropped).
        """
        with self._condition:
            if len(self._waiting) >= self._limit:
                ahead = [r.model for r in self._waiting]
                retry_after = estimator.estimate_wait_seconds(
                    model=request.model, resident=resident, ahead_models=ahead
                )
                raise ModelMoraRefusal("busy", retry_after_seconds=max(retry_after, 1))
            self._waiting.append(request)
            self._condition.notify_all()

    def withdraw(self, request_id: uuid.UUID) -> bool:
        """True if a still-waiting request was removed (FR-013); false once it has started."""
        with self._condition:
            for request in self._waiting:
                if request.request_id == request_id:
                    self._waiting.remove(request)
                    return True
            return False

    def standing(self, request_id: uuid.UUID) -> LineStanding | None:
        """Where `request_id` stands now, or `None` once it has left the line entirely
        (finished, failed or withdrawn -- `RequestStore` is the record of that)."""
        with self._condition:
            if self._running is not None and self._running.request_id == request_id:
                return LineStanding(position=0, ahead_models=[])
            ahead: list[ModelRef] = []
            if self._running is not None:
                ahead.append(self._running.model)
            for index, request in enumerate(self._waiting, start=1):
                if request.request_id == request_id:
                    return LineStanding(position=index, ahead_models=ahead)
                ahead.append(request.model)
            return None

    def wait_for_next(
        self,
        *,
        pick: Callable[[list[QueuedRequest]], QueuedRequest],
        timeout: float | None = None,
    ) -> QueuedRequest | None:
        """Blocks until a request is waiting, then hands the worker the one `pick` chose.

        `None` on timeout, so the worker's loop can come up for air periodically (to
        check for idle models to unload, and to notice it has been asked to stop).
        """
        with self._condition:
            if not self._condition.wait_for(lambda: bool(self._waiting), timeout=timeout):
                return None
            chosen = pick(list(self._waiting))
            self._waiting.remove(chosen)
            self._running = chosen
            return chosen

    def finish_running(self) -> None:
        with self._condition:
            self._running = None
            self._condition.notify_all()

    def __len__(self) -> int:
        with self._condition:
            return len(self._waiting)
