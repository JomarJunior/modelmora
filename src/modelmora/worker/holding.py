"""Where a finished image's bytes live until collected or discarded (FR-030, FR-032, R-7).

A temporary directory, never the registry: this is the one place result content
outlives the request that produced it, and only for the holding time. Each store gets
its own fresh directory (`tempfile.mkdtemp`, equivalent to "wiped on startup"); `wipe()`
removes it, called on shutdown so nothing an image ever held survives the process.
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class _Held:
    path: Path
    held_until: datetime


class ImageHoldingStore:
    """Image bytes on disk, collectable by request id until `held_until` (FR-032)."""

    def __init__(self, *, directory: Path | None = None) -> None:
        self._directory = directory or Path(tempfile.mkdtemp(prefix="modelmora-images-"))
        self._directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._held: dict[uuid.UUID, _Held] = {}

    def put(self, request_id: uuid.UUID, png_bytes: bytes, *, held_until: datetime) -> None:
        path = self._directory / f"{request_id}.png"
        path.write_bytes(png_bytes)
        with self._lock:
            self._held[request_id] = _Held(path=path, held_until=held_until)

    def get(self, request_id: uuid.UUID, *, now: datetime | None = None) -> bytes | None:
        moment = now or datetime.now(UTC)
        with self._lock:
            held = self._held.get(request_id)
            if held is None:
                return None
            if held.held_until <= moment:
                self._discard_locked(request_id)
                return None
        return held.path.read_bytes()

    def _discard_locked(self, request_id: uuid.UUID) -> None:
        held = self._held.pop(request_id, None)
        if held is not None:
            held.path.unlink(missing_ok=True)

    def discard_expired(self, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        with self._lock:
            expired = [rid for rid, held in self._held.items() if held.held_until <= moment]
            for request_id in expired:
                self._discard_locked(request_id)

    def wipe(self) -> None:
        """Removes every held image and the directory itself (startup and shutdown, R-7)."""
        with self._lock:
            self._held.clear()
        shutil.rmtree(self._directory, ignore_errors=True)
