"""T034: a caller sees only its own requests (FR-017).

Written before `api/requests.py`'s status and withdraw paths are extended for the
queue (T035), since access control is gate logic Principle VII requires tested first.
The isolation itself (`RequestStore.get` and `Line`-backed `withdraw_request` checking
`record.caller`) predates this task, so this test also guards against Phase 5's queue
work accidentally loosening it.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.conftest import OTHER_TOKEN


def _submit_text(client: TestClient) -> str:
    response = client.post(
        "/modelmora/v1/requests", json={"kind": "text", "instructions": "a private thought"}
    )
    assert response.status_code == 202
    return response.json()["requestId"]  # type: ignore[no-any-return]


def test_a_caller_cannot_read_another_callers_request(client: TestClient) -> None:
    request_id = _submit_text(client)

    other = TestClient(client.app, headers={"Authorization": f"Bearer {OTHER_TOKEN}"})
    response = other.get(f"/modelmora/v1/requests/{request_id}")

    assert response.status_code == 404


def test_a_caller_cannot_withdraw_another_callers_request(client: TestClient) -> None:
    request_id = _submit_text(client)

    other = TestClient(client.app, headers={"Authorization": f"Bearer {OTHER_TOKEN}"})
    withdrawal = other.delete(f"/modelmora/v1/requests/{request_id}")

    assert withdrawal.status_code == 404
    # The real owner still sees its own request, undisturbed by the other caller's
    # attempt (waiting or already done, but never "withdrawn").
    own_view = client.get(f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": 5})
    assert own_view.json()["state"] != "withdrawn"


def test_availability_reveals_nothing_caller_specific(client: TestClient) -> None:
    _submit_text(client)

    other = TestClient(client.app, headers={"Authorization": f"Bearer {OTHER_TOKEN}"})
    response = other.get("/modelmora/v1/availability")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"state", "queueLength", "servable"}


def test_no_caller_token_at_all_is_refused(client: TestClient) -> None:
    anonymous = TestClient(client.app)

    response = anonymous.get("/modelmora/v1/availability")

    assert response.status_code == 401
