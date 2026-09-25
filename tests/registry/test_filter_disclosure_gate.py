"""An undisclosable built-in filter is never servable (T037a, FR-008, spec Edge Cases).

The team member judges a model's filter behavior exactly as they judge its licence;
**ModelMora** only records the judgment. `none` and `disclosed` are both servable --
either there is no filter, or its effect can be reported (`filterNote`, T037's sibling
in `worker/results.py`); `undisclosable` never is, whatever the licence says.
"""

from __future__ import annotations

import pytest

from modelmora.messages import FilterDisclosure
from modelmora.registry.registry import ModelRecord, ModelRegistry


def _add(registry: ModelRegistry, *, name: str, filter_disclosure: FilterDisclosure) -> ModelRecord:
    return registry.add_model(
        name=name,
        version="1.0",
        kind="text",
        source="https://example.invalid/weights",
        weights_digest="sha256:test",
        added_by="team-member",
        license_name="Synthetic-Open-License",
        license_source="https://example.invalid/license",
        license_confirmed_by="team-member",
        filter_disclosure=filter_disclosure,
    )


def test_undisclosable_filter_is_never_servable_even_with_a_complete_licence() -> None:
    registry = ModelRegistry()
    _add(registry, name="synthetic-undisclosable-model", filter_disclosure="undisclosable")
    assert registry.list_servable() == []
    assert registry.resolve("synthetic-undisclosable-model", "1.0") is None


@pytest.mark.parametrize("disclosure", ["none", "disclosed"])
def test_none_or_disclosed_filter_behavior_is_servable(disclosure: FilterDisclosure) -> None:
    registry = ModelRegistry()
    _add(registry, name="synthetic-reportable-model", filter_disclosure=disclosure)
    servable = registry.list_servable()
    assert [m.name for m in servable] == ["synthetic-reportable-model"]


def test_undisclosable_model_cannot_become_a_default() -> None:
    registry = ModelRegistry()
    _add(registry, name="synthetic-undisclosable-model", filter_disclosure="undisclosable")
    with pytest.raises(ValueError):
        registry.set_default("text", "synthetic-undisclosable-model", "1.0")
