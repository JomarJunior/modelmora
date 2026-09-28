"""`build_runner` chooses the right runner by kind and file format (T056, T057).

No GPU: constructing a runner never loads it (`runners/text.py`, `runners/image.py`
and `runners/llamacpp.py` all defer their heavy imports into `load()`), so this only
checks which class comes back and what footprint it declares upfront -- proven
against tiny synthetic files, never real weights.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from modelmora.registry.store import ModelRecord, ServicePeriod
from modelmora.runners.build import build_runner, declared_footprint_hint
from modelmora.runners.image import ImageRunner
from modelmora.runners.llamacpp import _OVERHEAD_BYTES_PER_CONTEXT_TOKEN as _LLAMACPP_OVERHEAD
from modelmora.runners.llamacpp import LlamaCppTextRunner
from modelmora.runners.text import TextRunner

_NOW = datetime.now(UTC)
_IN_SERVICE = (ServicePeriod(started_at=_NOW, ended_at=None),)


def _record(**overrides: object) -> ModelRecord:
    base: dict[str, object] = dict(
        id=1,
        name="synthetic-model",
        version="1.0",
        kind="text",
        reads_images=False,
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        source="local fixture",
        weights_digest="sha256:synthetic",
        added_by="team-member",
        added_at=_NOW,
        license_confirmed_by="team-member",
        license_confirmed_at=_NOW,
        filter_disclosure="none",
        service_periods=_IN_SERVICE,
        local_path=None,
        companion_paths={},
    )
    base.update(overrides)
    return ModelRecord(**base)  # type: ignore[arg-type]


def test_no_local_path_means_no_runner() -> None:
    assert build_runner(_record(local_path=None)) is None


def test_a_gguf_text_model_gets_the_llamacpp_runner(tmp_path: Path) -> None:
    gguf = tmp_path / "synthetic-model.gguf"
    gguf.write_bytes(b"not a real gguf file, just needs a size")
    mmproj = tmp_path / "mmproj.gguf"
    mmproj.write_bytes(b"not a real mmproj either")

    record = _record(
        reads_images=True,
        local_path=str(gguf),
        companion_paths={"mmproj": str(mmproj)},
    )
    runner = build_runner(record)

    assert isinstance(runner, LlamaCppTextRunner)
    assert runner.name == "synthetic-model"
    assert runner.reads_images is True
    # File sizes plus the KV cache overhead for the runner's default context window
    # (T063) -- calibrated, not zero, so eviction math never assumes a `.gguf` model
    # costs only what its files weigh on disk.
    expected_overhead = int(4096 * _LLAMACPP_OVERHEAD)
    assert (
        runner.declared_footprint_bytes()
        == gguf.stat().st_size + mmproj.stat().st_size + expected_overhead
    )


def test_a_directory_text_model_gets_the_transformers_runner(tmp_path: Path) -> None:
    weights_dir = tmp_path / "synthetic-text-dir"
    weights_dir.mkdir()
    (weights_dir / "model.safetensors").write_bytes(b"synthetic weights")
    (weights_dir / "config.json").write_bytes(b"{}")

    runner = build_runner(_record(local_path=str(weights_dir)))

    assert isinstance(runner, TextRunner)
    assert runner.declared_footprint_bytes() == declared_footprint_hint(weights_dir)
    assert runner.declared_footprint_bytes() > 0


def test_a_single_file_image_model_gets_the_image_runner(tmp_path: Path) -> None:
    checkpoint = tmp_path / "synthetic-checkpoint.safetensors"
    checkpoint.write_bytes(b"synthetic sdxl-shaped checkpoint bytes")

    runner = build_runner(_record(kind="image", local_path=str(checkpoint)))

    assert isinstance(runner, ImageRunner)
    assert runner.declared_footprint_bytes() == checkpoint.stat().st_size


def test_a_directory_image_model_gets_the_image_runner_too(tmp_path: Path) -> None:
    weights_dir = tmp_path / "synthetic-image-dir"
    weights_dir.mkdir()
    (weights_dir / "model_index.json").write_bytes(b"{}")

    runner = build_runner(_record(kind="image", local_path=str(weights_dir)))

    assert isinstance(runner, ImageRunner)


def test_declared_footprint_hint_of_a_missing_path_is_zero(tmp_path: Path) -> None:
    assert declared_footprint_hint(tmp_path / "does-not-exist") == 0
