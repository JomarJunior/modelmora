"""The file digest check (T040, FR-022, R-8): a version mismatch refuses to serve and
tells the team, on the one channel plan.md names (a `WARNING` line naming the model,
version and expected digest, plus a non-zero exit from `modelmora model verify`).

Small synthetic files stand in for real model weights (FR-033): the digest is computed
the same way over a fixture directory as it would be over real weights.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.registry import ModelRegistry
from modelmora.registry.verify import compute_digest, verify_before_load


@pytest.fixture
def weights_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "weights"
    directory.mkdir()
    (directory / "config.json").write_text('{"hidden_size": 4}')
    (directory / "weights.bin").write_bytes(b"synthetic-weights-not-a-real-model")
    return directory


def test_digest_is_stable_over_unchanged_files(weights_dir: Path) -> None:
    assert compute_digest(weights_dir) == compute_digest(weights_dir)


def test_digest_changes_when_a_file_changes(weights_dir: Path) -> None:
    before = compute_digest(weights_dir)
    (weights_dir / "weights.bin").write_bytes(b"a different set of bytes entirely")
    assert compute_digest(weights_dir) != before


def test_verify_before_load_passes_when_files_match(weights_dir: Path) -> None:
    registry = ModelRegistry()
    record = registry.add_model(
        name="synthetic-verified-model",
        version="1.0",
        kind="text",
        source="local fixture",
        weights_digest=compute_digest(weights_dir),
        added_by="team-member",
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        license_confirmed_by="team-member",
    )
    verify_before_load(record, weights_dir)  # raises nothing


def test_verify_before_load_refuses_and_warns_on_mismatch(
    weights_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    registry = ModelRegistry()
    record = registry.add_model(
        name="synthetic-verified-model",
        version="1.0",
        kind="text",
        source="local fixture",
        weights_digest=compute_digest(weights_dir),
        added_by="team-member",
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        license_confirmed_by="team-member",
    )
    (weights_dir / "weights.bin").write_bytes(b"someone replaced the file on disk")

    with caplog.at_level(logging.WARNING, logger="modelmora.registry"):
        with pytest.raises(ModelMoraRefusal) as excinfo:
            verify_before_load(record, weights_dir)

    assert excinfo.value.reason == "model_unavailable"
    [warning] = caplog.records
    assert "synthetic-verified-model" in warning.message
    assert "1.0" in warning.message
    assert record.weights_digest in warning.message
