"""T073: a single-file image checkpoint's pipeline config is a registry companion.

`from_single_file` needs the pipeline's config and tokenizer files beside a bare
checkpoint. Recorded as the `config` companion, they reach the runner from the
registry alone (FR-020, FR-025), are covered by the same companion digest check as
any other companion (FR-022), and need nothing from `serve`'s environment -- no
`MODELMORA_SDXL_CONFIG_PATH`, no `HF_HOME` -- to load offline (FR-028). Against tiny
synthetic files, never real weights (FR-033).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modelmora import cli
from modelmora.config import Config
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.digest import compute_digest
from modelmora.registry.registry import ModelRegistry
from modelmora.registry.verify import verify_record_before_load
from modelmora.runners.build import build_runner
from modelmora.runners.image import ImageRunner


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELMORA_DB_PATH", str(tmp_path / "registry.db"))
    monkeypatch.delenv("MODELMORA_SDXL_CONFIG_PATH", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic-checkpoint.safetensors"
    path.write_bytes(b"synthetic single-file checkpoint bytes")
    return path


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "synthetic-pipeline-config"
    (directory / "tokenizer").mkdir(parents=True)
    (directory / "model_index.json").write_text('{"synthetic": true}')
    (directory / "tokenizer" / "vocab.json").write_text('{"a": 0}')
    return directory


def _add_image_model(registry: ModelRegistry, checkpoint: Path) -> None:
    registry.add_model(
        name="synthetic-single-file-image",
        version="1.0",
        kind="image",
        source="local fixture",
        weights_digest=compute_digest(checkpoint),
        added_by="team-member",
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        license_confirmed_by="team-member",
        local_path=str(checkpoint),
    )


def test_the_config_companion_reaches_the_image_runner_from_the_registry_alone(
    checkpoint: Path, config_dir: Path
) -> None:
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)
    registry.add_companion(
        "synthetic-single-file-image", "1.0", role="config", path=str(config_dir)
    )

    record = registry.resolve_record("synthetic-single-file-image", "1.0")
    assert record is not None
    runner = build_runner(record)

    assert isinstance(runner, ImageRunner)
    assert runner.sdxl_config_path == str(config_dir)


def test_adding_a_companion_records_its_digest_and_a_changed_config_is_refused(
    checkpoint: Path, config_dir: Path
) -> None:
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)
    registry.add_companion(
        "synthetic-single-file-image", "1.0", role="config", path=str(config_dir)
    )
    record = registry.resolve_record("synthetic-single-file-image", "1.0")
    assert record is not None
    assert record.companion_digests["config"] == compute_digest(config_dir)

    verify_record_before_load(record)  # unchanged: raises nothing

    (config_dir / "model_index.json").write_text('{"synthetic": false}')
    with pytest.raises(ModelMoraRefusal) as excinfo:
        verify_record_before_load(record)
    assert excinfo.value.reason == "model_unavailable"


@pytest.mark.parametrize(
    "bad_path",
    ["https://example.invalid/pipeline-config", "org/pipeline-config", "relative/config"],
)
def test_a_companion_that_is_not_on_this_studio_is_refused(checkpoint: Path, bad_path: str) -> None:
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)

    with pytest.raises(ValueError):
        registry.add_companion("synthetic-single-file-image", "1.0", role="config", path=bad_path)


def test_a_recorded_companion_is_never_silently_replaced(
    checkpoint: Path, config_dir: Path, tmp_path: Path
) -> None:
    """Replacing a companion would change what "that exact version" means (FR-022)."""
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)
    registry.add_companion(
        "synthetic-single-file-image", "1.0", role="config", path=str(config_dir)
    )
    other = tmp_path / "other-config"
    other.mkdir()

    with pytest.raises(ValueError):
        registry.add_companion("synthetic-single-file-image", "1.0", role="config", path=str(other))


def test_a_companion_for_a_model_not_on_record_is_refused(config_dir: Path) -> None:
    registry = ModelRegistry(Config.from_env().db_path)

    with pytest.raises(ValueError):
        registry.add_companion("synthetic-never-added", "1.0", role="config", path=str(config_dir))


def test_the_cli_adds_a_companion_to_an_existing_record(
    checkpoint: Path, config_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-025: a team member attaches the config without changing code."""
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)

    exit_code = cli.main(
        [
            "model",
            "add-companion",
            "--name",
            "synthetic-single-file-image",
            "--version",
            "1.0",
            "--companion",
            f"config={config_dir}",
        ]
    )

    assert exit_code == 0
    capsys.readouterr()
    record = ModelRegistry(Config.from_env().db_path).resolve_record(
        "synthetic-single-file-image", "1.0"
    )
    assert record is not None
    assert record.companion_paths == {"config": str(config_dir)}


def test_the_cli_rejects_an_invalid_companion_with_a_nonzero_exit(
    checkpoint: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = ModelRegistry(Config.from_env().db_path)
    _add_image_model(registry, checkpoint)

    exit_code = cli.main(
        [
            "model",
            "add-companion",
            "--name",
            "synthetic-single-file-image",
            "--version",
            "1.0",
            "--companion",
            "config=https://example.invalid/pipeline-config",
        ]
    )

    assert exit_code == 1
    assert "URL" in capsys.readouterr().err
