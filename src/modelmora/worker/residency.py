"""GPU residency: which models are loaded, and how they get evicted (FR-009).

Eviction and idle-unload are invisible to callers, who see only a longer wait, never
a memory error. `declared_footprint_bytes()` is asked of the runner, real or faked
(R-10); this module makes no assumption about GPU internals beyond "the resident
footprints must fit within capacity".

Capacity detection for a real GPU (`torch.cuda.get_device_properties`) belongs to the
real image runner (T023, out of scope on hardware with no GPU); `DEFAULT_CAPACITY_BYTES`
below stands in for one Studio RTX 4090 (plan.md "Target Platform") until then.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from modelmora.runners.base import Runner

# plan.md: "one Linux or macOS machine with an RTX 4090 (24 GB)".
DEFAULT_CAPACITY_BYTES = 24 * 1024**3


class CannotFit(Exception):
    """A model's declared footprint alone exceeds capacity (spec Edge Cases)."""


@dataclass
class _Resident:
    runner: Runner
    last_used: float


class Residency:
    """Owns which runners are loaded, evicting least-recently-used ones to make room."""

    def __init__(self, capacity_bytes: int = DEFAULT_CAPACITY_BYTES) -> None:
        self._capacity_bytes = capacity_bytes
        self._lock = threading.Lock()
        self._resident: dict[tuple[str, str], _Resident] = {}

    @staticmethod
    def _key(runner: Runner) -> tuple[str, str]:
        return (runner.name, runner.version)

    def fits_alone(self, footprint_bytes: int) -> bool:
        """Whether a model of this footprint could ever be resident, alone (Edge Cases)."""
        return footprint_bytes <= self._capacity_bytes

    def _resident_bytes(self, excluding: tuple[str, str] | None) -> int:
        return sum(
            r.runner.declared_footprint_bytes()
            for key, r in self._resident.items()
            if key != excluding
        )

    def ensure_loaded(self, runner: Runner) -> None:
        """Loads `runner`, evicting least-recently-used residents to make room.

        Raises `CannotFit` if the runner's own footprint exceeds capacity, even alone.
        Callers that must refuse before queueing (FR-011) check `fits_alone` first
        (`api/validate.py`); this is the belt for the worker's own use.
        """
        footprint = runner.declared_footprint_bytes()
        if not self.fits_alone(footprint):
            raise CannotFit(
                f"{runner.name} v{runner.version} needs {footprint} bytes, more than "
                f"the {self._capacity_bytes} byte capacity"
            )
        with self._lock:
            key = self._key(runner)
            if runner.is_loaded():
                self._resident[key] = _Resident(runner=runner, last_used=time.monotonic())
                return

            while self._resident_bytes(excluding=key) + footprint > self._capacity_bytes:
                self._evict_least_recently_used_locked()

            runner.load()
            self._resident[key] = _Resident(runner=runner, last_used=time.monotonic())

    def _evict_least_recently_used_locked(self) -> None:
        if not self._resident:
            raise CannotFit("no resident model left to evict, yet still over capacity")
        lru_key = min(self._resident, key=lambda k: self._resident[k].last_used)
        evicted = self._resident.pop(lru_key)
        evicted.runner.unload()

    def touch(self, runner: Runner) -> None:
        """Marks `runner` as just used, for LRU and idle-unload accounting."""
        with self._lock:
            resident = self._resident.get(self._key(runner))
            if resident is not None:
                resident.last_used = time.monotonic()

    def unload_idle(self, idle_seconds: float) -> list[Runner]:
        """Unloads every resident model unused for at least `idle_seconds`.

        Called periodically by the generation worker (T032); nothing here starts a
        timer of its own.
        """
        now = time.monotonic()
        unloaded: list[Runner] = []
        with self._lock:
            idle_keys = [
                key for key, r in self._resident.items() if now - r.last_used >= idle_seconds
            ]
            for key in idle_keys:
                resident = self._resident.pop(key)
                resident.runner.unload()
                unloaded.append(resident.runner)
        return unloaded

    def resident_runners(self) -> list[Runner]:
        with self._lock:
            return [r.runner for r in self._resident.values()]
