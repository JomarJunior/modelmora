"""Every result names a model whose record holds a licence -- retirement included
(T043, FR-023, SC-005).
"""

from __future__ import annotations

from starlette.testclient import TestClient

from modelmora.api.state import AppState


def test_every_result_names_a_model_whose_record_holds_a_licence(
    client: TestClient, state: AppState
) -> None:
    response = client.post(
        "/modelmora/v1/requests",
        json={"kind": "text", "instructions": "say something for the licence trail"},
    )
    assert response.status_code == 202
    request_id = response.json()["requestId"]

    status = client.get(f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": 5}).json()
    assert status["state"] == "done"
    model_name = status["result"]["model"]["name"]
    model_version = status["result"]["model"]["version"]

    record = state.registry.resolve_record(model_name, model_version)
    assert record is not None
    assert record.license_name  # SC-005: the record the result names holds a licence

    state.registry.retire(model_name, model_version)

    retired = state.registry.resolve_record(model_name, model_version)
    assert retired is not None
    assert retired.license_name == record.license_name  # FR-023: the licence survives
    assert not retired.in_service
    # No longer servable, so a caller could not get this exact result again -- but the
    # trail this test just checked is what SC-005 measures, not what the API returns.
    assert state.registry.resolve(model_name, model_version) is None
