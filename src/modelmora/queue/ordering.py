"""Which waiting request the worker takes next (T031, R-5, FR-019).

Arrival order, with one exception: a request whose model is already resident may run
ahead of an older one that would need a load, so the GPU is not made to thrash between
two models. No request may be favored this way forever: once the head of the line has
waited the bounded overtaking time, it runs next regardless of residency.

"How long has it been overtaken" is read here as "how long has it been sitting at the
head of the line without running" -- the same clock whether it was passed over once or
several times in a row, and it depends only on the model and the arrival time, never
on the caller or the persona (FR-019, Principle I).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from modelmora.queue.line import QueuedRequest


def pick_next(
    waiting: Sequence[QueuedRequest],
    resident_keys: set[tuple[str, str]],
    overtaking_seconds: float,
    *,
    now: datetime | None = None,
) -> QueuedRequest:
    """The request the worker should run next; raises if nothing is waiting."""
    if not waiting:
        raise ValueError("pick_next called with nothing waiting")
    moment = now or datetime.now(UTC)
    head = waiting[0]
    if (moment - head.submitted_at).total_seconds() >= overtaking_seconds:
        return head
    if (head.model.name, head.model.version) in resident_keys:
        return head
    for candidate in waiting[1:]:
        if (candidate.model.name, candidate.model.version) in resident_keys:
            return candidate
    return head
