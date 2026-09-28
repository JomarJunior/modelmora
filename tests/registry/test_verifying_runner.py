"""`VerifyingRunner` checks a record's files against its recorded digest before its
very first real `load()` in `serve` (T062, FR-022) -- companion files (a vision
projector) included, not only the main weights. Against tiny synthetic files, never
real weights (FR-033).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.digest import compute_digest
from modelmora.registry.store import ModelRecord, ServicePeriod
from modelmora.registry.verify import VerifyingRunner
from modelmora.runners.base import GeneratedText, Runner

_NOW = datetime.now(UTC)
_IN_SERVICE = (ServicePeriod(started_at=_NOW, ended_at=None),)


class _CountingRunner(Runner):
    kind = "text"

    def __init__(self) -> None:
        self.name = "synthetic-verified-model"
        self.version = "1.0"
        self.reads_images = False
        self.load_calls = 0
        self._loaded = False

    def declared_footprint_bytes(self) -> int:
        return 1

    def load(self) -> None:
        self.load_calls += 1
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def generate_text(self, **kwargs: object) -> GeneratedText:
        return GeneratedText(text="synthetic", settings_used={})


def _record(**overrides: object) -> ModelRecord:
    base: dict[str, object] = dict(
        id=1,
        name="synthetic-verified-model",
        version="1.0",
        kind="text",
        reads_images=False,
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        source="local fixture",
        weights_digest="sha256:placeholder",
        added_by="team-member",
        added_at=_NOW,
        license_confirmed_by="team-member",
        license_confirmed_at=_NOW,
        filter_disclosure="none",
        service_periods=_IN_SERVICE,
        local_path=None,
        companion_paths={},
        companion_digests={},
    )
    base.update(overrides)
    return ModelRecord(**base)  # type: ignore[arg-type]


def test_refuses_before_the_first_load_on_a_weights_mismatch(tmp_path: Path) -> None:
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic weights")
    record = _record(local_path=str(weights), weights_digest="sha256:wrong")
    inner = _CountingRunner()
    runner = VerifyingRunner(inner, record)

    with pytest.raises(ModelMoraRefusal) as excinfo:
        runner.load()

    assert excinfo.value.reason == "model_unavailable"
    assert inner.load_calls == 0


def test_refuses_before_the_first_load_on_a_companion_mismatch(tmp_path: Path) -> None:
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic weights")
    mmproj = tmp_path / "mmproj.bin"
    mmproj.write_bytes(b"synthetic mmproj")
    record = _record(
        local_path=str(weights),
        weights_digest=compute_digest(weights),
        companion_paths={"mmproj": str(mmproj)},
        companion_digests={"mmproj": "sha256:wrong"},
    )
    inner = _CountingRunner()
    runner = VerifyingRunner(inner, record)

    with pytest.raises(ModelMoraRefusal) as excinfo:
        runner.load()

    assert excinfo.value.reason == "model_unavailable"
    assert inner.load_calls == 0


def test_loads_when_everything_matches_and_verifies_only_once(tmp_path: Path) -> None:
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic weights")
    record = _record(local_path=str(weights), weights_digest=compute_digest(weights))
    inner = _CountingRunner()
    runner = VerifyingRunner(inner, record)

    runner.load()
    runner.unload()
    # Tampered after the first (and only) verification: a second load() must not
    # notice, proving verification happened once per process, not on every load.
    weights.write_bytes(b"a completely different file now")
    runner.load()

    assert inner.load_calls == 2


def test_a_companion_with_no_recorded_digest_is_not_checked(tmp_path: Path) -> None:
    """A companion added before this task existed has nothing to compare against
    yet (`registry/store.py`'s migration backfills one); until then it is simply not
    checked, not refused for a digest that was never computed."""
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic weights")
    mmproj = tmp_path / "mmproj.bin"
    mmproj.write_bytes(b"synthetic mmproj, unrecorded")
    record = _record(
        local_path=str(weights),
        weights_digest=compute_digest(weights),
        companion_paths={"mmproj": str(mmproj)},
        companion_digests={},
    )
    inner = _CountingRunner()
    runner = VerifyingRunner(inner, record)

    runner.load()  # raises nothing

    assert inner.load_calls == 1
