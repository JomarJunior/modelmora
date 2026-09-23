"""Every message model's generated schema matches the hub's `modelmora-v1.yaml`.

Fails when either side changes alone: a field renamed or dropped in `messages.py`
without updating the contract, or the reverse.
"""

from __future__ import annotations

import pytest

from modelmora import contract, messages
from tests.schema_compare import diff

NAMED_SCHEMAS: list[tuple[str, type]] = [
    ("ModelRef", messages.ModelRef),
    ("TextRequest", messages.TextRequest),
    ("ImageRequest", messages.ImageRequest),
    ("Accepted", messages.Accepted),
    ("RequestStatus", messages.RequestStatus),
    ("Result", messages.Result),
    ("ServableModel", messages.ServableModel),
    ("Availability", messages.Availability),
    ("Refusal", messages.Refusal),
]


@pytest.mark.parametrize("schema_name,model", NAMED_SCHEMAS, ids=[n for n, _ in NAMED_SCHEMAS])
def test_model_matches_hub_schema(schema_name: str, model: type) -> None:
    hub_doc = contract.load_contract()
    hub_schema = contract.schema(schema_name)
    hub_side, model_side = diff(hub_schema, hub_doc, model)
    assert hub_side == model_side, f"{schema_name} drifted from the hub contract"
