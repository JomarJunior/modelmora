"""A record without a complete, confirmed licence is never served (T037, FR-021).

US4 acceptance scenario 2: a model on record without a licence, or without a team
member's confirmation, is refused when a caller asks for it, and never loaded.
"""

from __future__ import annotations

import pytest

from modelmora.api.validate import resolve_text_model
from modelmora.messages import TextRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.registry import ModelRecord, ModelRegistry


def _add(
    registry: ModelRegistry,
    *,
    license_name: str | None = None,
    license_source: str | None = None,
    license_confirmed_by: str | None = None,
) -> ModelRecord:
    return registry.add_model(
        name="synthetic-licenced-model",
        version="1.0",
        kind="text",
        source="https://example.invalid/weights",
        weights_digest="sha256:test",
        added_by="team-member",
        license_name=license_name,
        license_source=license_source,
        license_confirmed_by=license_confirmed_by,
    )


def test_missing_licence_name_is_never_servable() -> None:
    registry = ModelRegistry()
    _add(registry, license_source="https://example.invalid/license", license_confirmed_by="team")
    assert registry.list_servable() == []
    assert registry.resolve("synthetic-licenced-model", "1.0") is None


def test_missing_licence_source_is_never_servable() -> None:
    registry = ModelRegistry()
    _add(registry, license_name="Synthetic-Open-License", license_confirmed_by="team")
    assert registry.list_servable() == []
    assert registry.resolve("synthetic-licenced-model", "1.0") is None


def test_missing_confirmation_is_never_servable() -> None:
    registry = ModelRegistry()
    _add(
        registry,
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
    )
    assert registry.list_servable() == []
    assert registry.resolve("synthetic-licenced-model", "1.0") is None


def test_complete_confirmed_record_is_servable() -> None:
    registry = ModelRegistry()
    _add(
        registry,
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        license_confirmed_by="team",
    )
    servable = registry.list_servable()
    assert [m.name for m in servable] == ["synthetic-licenced-model"]
    assert registry.resolve("synthetic-licenced-model", "1.0") is not None


def test_a_caller_naming_an_incomplete_model_is_refused_and_nothing_is_loaded() -> None:
    """The model exists on record but is refused exactly as an unknown one would be:
    a caller has no way to act differently on "not on record" versus "on record but
    incomplete", and no wire message may say more (registry.py's documented reading of
    FR-011 and FR-017)."""
    registry = ModelRegistry()
    _add(registry, license_name="Synthetic-Open-License")
    request = TextRequest.model_validate(
        {
            "kind": "text",
            "model": {"name": "synthetic-licenced-model", "version": "1.0"},
            "instructions": "say something",
        }
    )
    with pytest.raises(ModelMoraRefusal) as excinfo:
        resolve_text_model(registry, request)
    assert excinfo.value.reason == "unknown_model"


def test_the_default_slot_cannot_point_at_an_incomplete_record() -> None:
    registry = ModelRegistry()
    _add(registry, license_name="Synthetic-Open-License")
    with pytest.raises(ValueError):
        registry.set_default("text", "synthetic-licenced-model", "1.0")
