"""`modelmora model add|list|retire|verify|set-default` (T041), and `--all` reads the
whole licence trail including retired models with their service dates (T042, SC-006).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modelmora import cli
from modelmora.config import Config
from modelmora.registry.registry import ModelRegistry


@pytest.fixture
def weights_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "weights"
    directory.mkdir()
    (directory / "weights.bin").write_bytes(b"synthetic-weights-not-a-real-model")
    return directory


@pytest.fixture(autouse=True)
def _db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELMORA_DB_PATH", str(tmp_path / "registry.db"))


def test_add_then_list_shows_the_new_model(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-cli-model",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
            "--license",
            "Synthetic-Open-License",
            "--license-source",
            "https://example.invalid/license",
            "--confirm-license",
        ]
    )
    assert exit_code == 0
    capsys.readouterr()

    assert cli.main(["model", "list"]) == 0
    listed = capsys.readouterr().out
    assert "synthetic-cli-model" in listed
    assert "servable" in listed


def test_an_incomplete_model_is_recorded_but_absent_from_the_default_list(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        cli.main(
            [
                "model",
                "add",
                "--name",
                "synthetic-incomplete-model",
                "--version",
                "1.0",
                "--kind",
                "text",
                "--source",
                "local fixture",
                "--weights-path",
                str(weights_dir),
            ]
        )
        == 0
    )
    capsys.readouterr()

    cli.main(["model", "list"])
    assert "synthetic-incomplete-model" not in capsys.readouterr().out

    cli.main(["model", "list", "--all"])
    assert "synthetic-incomplete-model" in capsys.readouterr().out


def test_retiring_a_model_keeps_it_in_the_all_listing_with_service_dates(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-retiring-model",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
            "--license",
            "Synthetic-Open-License",
            "--license-source",
            "https://example.invalid/license",
            "--confirm-license",
        ]
    )
    capsys.readouterr()

    retire_args = ["model", "retire", "--name", "synthetic-retiring-model", "--version", "1.0"]
    assert cli.main(retire_args) == 0
    capsys.readouterr()

    cli.main(["model", "list"])
    assert "synthetic-retiring-model" not in capsys.readouterr().out

    cli.main(["model", "list", "--all"])
    all_output = capsys.readouterr().out
    assert "synthetic-retiring-model" in all_output
    assert "->" in all_output  # the service period's start and end


def test_verify_matches_then_fails_after_the_files_change(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-verify-model",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
            "--license",
            "Synthetic-Open-License",
            "--license-source",
            "https://example.invalid/license",
            "--confirm-license",
        ]
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "model",
                "verify",
                "--name",
                "synthetic-verify-model",
                "--version",
                "1.0",
                "--weights-path",
                str(weights_dir),
            ]
        )
        == 0
    )
    capsys.readouterr()

    (weights_dir / "weights.bin").write_bytes(b"a tampered file")
    assert (
        cli.main(
            [
                "model",
                "verify",
                "--name",
                "synthetic-verify-model",
                "--version",
                "1.0",
                "--weights-path",
                str(weights_dir),
            ]
        )
        == 1
    )


def test_set_default_then_list_shows_it(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-default-model",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
            "--license",
            "Synthetic-Open-License",
            "--license-source",
            "https://example.invalid/license",
            "--confirm-license",
        ]
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "model",
                "set-default",
                "--slot",
                "text",
                "--name",
                "synthetic-default-model",
                "--version",
                "1.0",
            ]
        )
        == 0
    )
    capsys.readouterr()

    cli.main(["model", "list"])
    assert "default[text] = synthetic-default-model v1.0" in capsys.readouterr().out


def test_local_path_and_companions_round_trip_through_add(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T054-T057: what `serve` needs to build a real runner survives `model add`."""
    checkpoint = weights_dir / "weights.bin"
    mmproj = weights_dir / "mmproj.bin"
    mmproj.write_bytes(b"synthetic mmproj bytes")

    assert (
        cli.main(
            [
                "model",
                "add",
                "--name",
                "synthetic-local-path-model",
                "--version",
                "1.0",
                "--kind",
                "text",
                "--reads-images",
                "--source",
                "local fixture",
                "--weights-path",
                str(weights_dir),
                "--local-path",
                str(checkpoint),
                "--companion",
                f"mmproj={mmproj}",
                "--license",
                "Synthetic-Open-License",
                "--license-source",
                "https://example.invalid/license",
                "--confirm-license",
            ]
        )
        == 0
    )
    capsys.readouterr()

    registry = ModelRegistry(Config.from_env().db_path)
    record = registry.resolve_record("synthetic-local-path-model", "1.0")
    assert record is not None
    assert record.local_path == str(checkpoint)
    assert record.companion_paths == {"mmproj": str(mmproj)}


def test_an_invalid_local_path_is_rejected_with_a_nonzero_exit(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T070: a URL or a relative path is refused, not silently recorded."""
    exit_code = cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-bad-local-path",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
            "--local-path",
            "https://example.invalid/weights.safetensors",
        ]
    )
    assert exit_code == 1
    assert "URL" in capsys.readouterr().err

    registry = ModelRegistry(Config.from_env().db_path)
    assert registry.resolve_record("synthetic-bad-local-path", "1.0") is None


def test_local_path_defaults_to_the_weights_path(
    weights_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(
        [
            "model",
            "add",
            "--name",
            "synthetic-default-local-path",
            "--version",
            "1.0",
            "--kind",
            "text",
            "--source",
            "local fixture",
            "--weights-path",
            str(weights_dir),
        ]
    )
    capsys.readouterr()

    registry = ModelRegistry(Config.from_env().db_path)
    record = registry.resolve_record("synthetic-default-local-path", "1.0")
    assert record is not None
    assert record.local_path == str(weights_dir)
    assert record.companion_paths == {}
