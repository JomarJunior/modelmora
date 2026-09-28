"""GPU residency: which models are loaded, and how they get evicted (FR-009).

Eviction and idle-unload are invisible to callers, who see only a longer wait, never
a memory error. `declared_footprint_bytes()` is asked of the runner, real or faked
(R-10); this module makes no assumption about GPU internals beyond "the resident
footprints must fit within capacity".

`DEFAULT_CAPACITY_BYTES` stands in for one Studio RTX 4090 (plan.md "Target
Platform"): the fixed value test mode, CI and every existing test keep using
(`Residency()` with no `capacity_bytes`, unchanged from before T063). `serve` itself
(`cli.py`, non-test-mode) asks `detect_gpu_capacity_bytes()` for the real GPU's own
free memory instead, and passes that in explicitly -- capacity is measured once at
startup, not reprobed per request.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass

from modelmora.refusals import ModelMoraRefusal
from modelmora.runners.base import Runner

# The one channel for telling the team (plan.md): a WARNING line in the operator log.
logger = logging.getLogger("modelmora.worker")

# plan.md: "one Linux or macOS machine with an RTX 4090 (24 GB)".
DEFAULT_CAPACITY_BYTES = 24 * 1024**3


def detect_gpu_capacity_bytes() -> int | None:
    """Free GPU memory right now, real hardware only (T063); `None` with no GPU
    visible (stand-ins and CI keep the fixed `DEFAULT_CAPACITY_BYTES` instead,
    R-10). Free rather than total: measured on the Studio, something else (the
    desktop compositor) already holds a few hundred MiB before ModelMora starts,
    and reserving for that is more honest than assuming the whole card is ours.

    Tried in order: `nvidia-smi` (works with no Python CUDA package installed at
    all), then `torch.cuda.mem_get_info` if the `gpu` extra is present. Neither is
    imported or run at module load, only when a real `serve` actually calls this.
    """
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        total_mib, used_mib = result.stdout.strip().splitlines()[0].split(",")
        return (int(total_mib) - int(used_mib)) * 1024 * 1024
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        pass
    try:
        import torch

        if torch.cuda.is_available():
            free_bytes, _total_bytes = torch.cuda.mem_get_info(0)
            return int(free_bytes)
    except ImportError:
        pass
    return None


def _unavailable(runner: Runner) -> ModelMoraRefusal:
    return ModelMoraRefusal(
        "model_unavailable",
        detail=f"{runner.name} v{runner.version} could not be loaded on this Studio",
    )


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
        # Models whose load failed in this process (T072). Known broken until the
        # team fixes the files and restarts `serve`; never retried per request.
        self._unloadable: set[tuple[str, str]] = set()

    @staticmethod
    def _key(runner: Runner) -> tuple[str, str]:
        return (runner.name, runner.version)

    def is_unloadable(self, runner: Runner) -> bool:
        """Whether `runner`'s load already failed in this process (T072, spec Edge Cases)."""
        with self._lock:
            return self._key(runner) in self._unloadable

    def fits_alone(self, footprint_bytes: int) -> bool:
        """Whether a model of this footprint could ever be resident, alone (Edge Cases)."""
        return footprint_bytes <= self._capacity_bytes

    def _resident_bytes(self, excluding: tuple[str, str] | None) -> int:
        return sum(
            r.runner.declared_footprint_bytes()
            for key, r in self._resident.items()
            if key != excluding
        )

    def ensure_loaded(self, runner: Runner, *, footprint_override: int | None = None) -> None:
        """Loads `runner`, evicting least-recently-used residents to make room.

        `footprint_override`, when given, is the peak footprint for the *specific*
        request about to run -- weights plus that request's own runtime overhead
        (T063: SDXL activations sized to the request, a llama.cpp KV cache), computed
        once at admission (`api/validate.py`) and carried on the `QueuedRequest`
        (`worker/worker.py`). Every *other* resident runner still reports through its
        own `declared_footprint_bytes()`, its resting weights-only figure: only the
        runner about to actually generate incurs activation overhead, and by
        construction (one worker, one generation at a time) nothing else is
        generating while this decision is made.

        Raises `CannotFit` if the runner's own footprint exceeds capacity, even alone.
        Callers that must refuse before queueing (FR-011) check `fits_alone` first
        (`api/validate.py`); this is the belt for the worker's own use.
        """
        footprint = (
            footprint_override
            if footprint_override is not None
            else runner.declared_footprint_bytes()
        )
        if not self.fits_alone(footprint):
            raise CannotFit(
                f"{runner.name} v{runner.version} needs {footprint} bytes, more than "
                f"the {self._capacity_bytes} byte capacity"
            )
        with self._lock:
            key = self._key(runner)
            if key in self._unloadable:
                raise _unavailable(runner)
            if runner.is_loaded():
                self._resident[key] = _Resident(runner=runner, last_used=time.monotonic())
                return

            while self._resident_bytes(excluding=key) + footprint > self._capacity_bytes:
                self._evict_least_recently_used_locked()

            try:
                runner.load()
            except Exception as exc:
                # A model that cannot be loaded at all is `model_unavailable`, never a
                # generation failure (spec Edge Cases, T072). A digest mismatch has
                # already told the team (`registry/verify.py`); anything else is told
                # here, with the error's own reason so the team can act on it (T074).
                # Safe under FR-030: `load()` is never handed a request, so nothing it
                # raises can carry request or result content.
                self._unloadable.add(key)
                if isinstance(exc, ModelMoraRefusal):
                    raise
                logger.warning(
                    "model could not be loaded: %s v%s (%s: %s); refusing it until serve restarts",
                    runner.name,
                    runner.version,
                    type(exc).__name__,
                    exc,
                )
                raise _unavailable(runner) from exc
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

    def resident_keys(self) -> set[tuple[str, str]]:
        """Which (name, version) pairs are on the GPU right now (`queue/ordering.py`, T031)."""
        with self._lock:
            return set(self._resident.keys())
