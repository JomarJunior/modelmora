"""The service binds 127.0.0.1 only and works with no network reachable (FR-027, FR-028)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from modelmora.api.app import AppState, InvalidBindHost, assert_loopback_host, create_app
from modelmora.config import BIND_HOST
from tests.conftest import CALLER_TOKEN, build_state


def test_loopback_host_is_accepted() -> None:
    assert_loopback_host(BIND_HOST)  # does not raise


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.1"])
def test_any_other_interface_is_refused(host: str) -> None:
    with pytest.raises(InvalidBindHost):
        assert_loopback_host(host)


def test_service_answers_with_no_real_network(state: AppState) -> None:
    """An in-process ASGI transport proves the whole path works without a socket or
    any reachable network, which is what FR-028 requires once models are local."""
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})
    response = client.get("/modelmora/v1/availability")
    assert response.status_code == 200
    assert response.json()["state"] == "running"


def test_missing_caller_token_is_refused() -> None:
    client = TestClient(create_app(build_state()))
    response = client.get("/modelmora/v1/availability")
    assert response.status_code == 401
    assert response.json()["reason"] == "invalid_request"
