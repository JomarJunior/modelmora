"""Honest wait estimates from this Studio's own history (FR-018, R-5, T033).

A rolling median of measured generation time per model, plus load time when the model
is not resident, plus the work already ahead in the line. The worker
(`worker/worker.py`) records every measurement after it happens; `api/requests.py`
reads them when accepting a request and when a caller asks about one. Nothing here
ever decides what runs next -- only `queue/ordering.py` does that, from arrival time
and residency alone, so an estimate can never become a lever for reordering work.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from collections.abc import Sequence

from modelmora.messages import ModelRef

# Enough samples to smooth one slow run without letting stale history linger.
_HISTORY_SIZE = 20

# Before a model has run even once there is no history to measure; SC-004 is only
# checked once every model has run at least once, so this placeholder never has to be
# accurate, only present so a first request still gets a number.
_DEFAULT_GENERATION_SECONDS = 1.0
_DEFAULT_LOAD_SECONDS = 1.0

_Key = tuple[str, str]


class Estimator:
    """This Studio's own measured history of generation and load time, per model."""

    def __init__(self, *, history_size: int = _HISTORY_SIZE) -> None:
        self._history_size = history_size
        self._generation: dict[_Key, deque[float]] = defaultdict(
            lambda: deque(maxlen=self._history_size)
        )
        self._load: dict[_Key, deque[float]] = defaultdict(lambda: deque(maxlen=self._history_size))

    @staticmethod
    def _key(model: ModelRef) -> _Key:
        return (model.name, model.version)

    def record_generation(self, model: ModelRef, seconds: float) -> None:
        self._generation[self._key(model)].append(max(seconds, 0.0))

    def record_load(self, model: ModelRef, seconds: float) -> None:
        self._load[self._key(model)].append(max(seconds, 0.0))

    def median_generation_seconds(self, model: ModelRef) -> float:
        samples = self._generation.get(self._key(model))
        return statistics.median(samples) if samples else _DEFAULT_GENERATION_SECONDS

    def median_load_seconds(self, model: ModelRef) -> float:
        samples = self._load.get(self._key(model))
        return statistics.median(samples) if samples else _DEFAULT_LOAD_SECONDS

    def estimate_wait_seconds(
        self, *, model: ModelRef, resident: bool, ahead_models: Sequence[ModelRef]
    ) -> int:
        """How long this request should wait: its own work plus everything ahead of it.

        Rounded up, never down: an estimate that undersells the wait is the dishonest
        direction (FR-018); overselling by a second is not.
        """
        own = self.median_generation_seconds(model)
        if not resident:
            own += self.median_load_seconds(model)
        ahead = sum(self.median_generation_seconds(m) for m in ahead_models)
        return math.ceil(own + ahead)
