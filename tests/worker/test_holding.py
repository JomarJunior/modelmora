"""Where a finished image lives, and for how long (T026, FR-030, FR-032, R-7).

A persona's work is held for its caller to collect and then discarded. This is the one
place result content outlives its request, so the bytes must actually leave the disk.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from modelmora.worker.holding import ImageHoldingStore

PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic bytes"


def _store(tmp_path: Path) -> ImageHoldingStore:
    return ImageHoldingStore(directory=tmp_path / "held")


def test_an_image_is_collectable_while_it_is_held(tmp_path: Path) -> None:
    store = _store(tmp_path)
    request_id = uuid.uuid4()

    store.put(request_id, PNG, held_until=datetime.now(UTC) + timedelta(hours=1))

    assert store.get(request_id) == PNG


def test_an_image_is_gone_once_its_holding_time_passes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    request_id = uuid.uuid4()
    store.put(request_id, PNG, held_until=datetime.now(UTC) - timedelta(seconds=1))

    assert store.get(request_id) is None
    assert list((tmp_path / "held").glob("*.png")) == [], "the bytes were left on disk"


def test_discard_expired_leaves_the_living_alone(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stale, fresh = uuid.uuid4(), uuid.uuid4()
    store.put(stale, PNG, held_until=datetime.now(UTC) - timedelta(seconds=1))
    store.put(fresh, PNG, held_until=datetime.now(UTC) + timedelta(hours=1))

    store.discard_expired()

    assert store.get(stale) is None
    assert store.get(fresh) == PNG


def test_an_unknown_request_holds_nothing(tmp_path: Path) -> None:
    assert _store(tmp_path).get(uuid.uuid4()) is None


def test_wipe_removes_every_held_image_and_its_directory(tmp_path: Path) -> None:
    """Called on shutdown: nothing a caller collected outlives the process."""
    store = _store(tmp_path)
    store.put(uuid.uuid4(), PNG, held_until=datetime.now(UTC) + timedelta(hours=1))
    directory = tmp_path / "held"
    assert list(directory.glob("*.png"))

    store.wipe()

    assert not directory.exists()


def test_each_store_starts_with_its_own_empty_directory() -> None:
    """No directory is given, so one is made fresh — the equivalent of wiped on startup."""
    first, second = ImageHoldingStore(), ImageHoldingStore()
    try:
        request_id = uuid.uuid4()
        first.put(request_id, PNG, held_until=datetime.now(UTC) + timedelta(hours=1))

        assert second.get(request_id) is None
    finally:
        first.wipe()
        second.wipe()
