"""`local_path` and every companion path are validated as existing, absolute paths on
this Studio when a model is added, rejecting a URL or a bare Hub identifier before
anything is recorded (T070, FR-026, FR-028).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modelmora.registry.registry import ModelRegistry


def _add(registry: ModelRegistry, **overrides: object) -> None:
    base: dict[str, object] = dict(
        name="synthetic-path-model",
        version="1.0",
        kind="text",
        source="local fixture",
        weights_digest="sha256:test",
        added_by="team-member",
    )
    base.update(overrides)
    registry.add_model(**base)  # type: ignore[arg-type]


def test_a_relative_local_path_is_rejected() -> None:
    registry = ModelRegistry()
    with pytest.raises(ValueError, match="absolute path"):
        _add(registry, local_path="relative/weights.bin")


def test_a_url_local_path_is_rejected() -> None:
    registry = ModelRegistry()
    with pytest.raises(ValueError, match="URL"):
        _add(registry, local_path="https://example.invalid/weights.safetensors")


def test_a_hub_identifier_local_path_is_rejected() -> None:
    """A bare Hub id (`org/repo`) is not an absolute filesystem path, so it is
    already caught by the same check as any other relative path."""
    registry = ModelRegistry()
    with pytest.raises(ValueError, match="absolute path"):
        _add(registry, local_path="the base SDXL pipeline")


def test_a_nonexistent_absolute_local_path_is_rejected(tmp_path: Path) -> None:
    registry = ModelRegistry()
    with pytest.raises(ValueError, match="does not exist"):
        _add(registry, local_path=str(tmp_path / "never-written.safetensors"))


def test_an_invalid_companion_path_is_rejected_and_names_its_role(tmp_path: Path) -> None:
    registry = ModelRegistry()
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="mmproj"):
        _add(
            registry,
            local_path=str(weights),
            companion_paths={"mmproj": "relative/mmproj.bin"},
        )


def test_a_valid_absolute_existing_local_path_and_companion_are_accepted(tmp_path: Path) -> None:
    registry = ModelRegistry()
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"synthetic")
    mmproj = tmp_path / "mmproj.bin"
    mmproj.write_bytes(b"synthetic companion")

    _add(
        registry,
        local_path=str(weights),
        companion_paths={"mmproj": str(mmproj)},
    )  # raises nothing

    record = registry.resolve_record("synthetic-path-model", "1.0")
    assert record is not None
    assert record.local_path == str(weights)
    assert record.companion_paths == {"mmproj": str(mmproj)}


def test_no_local_path_is_still_accepted_exactly_as_before() -> None:
    """A record added without one (the pre-T054 shape, or the quick `register()`
    test-fixture path) is unaffected: there is nothing to validate."""
    registry = ModelRegistry()
    _add(registry)  # raises nothing
