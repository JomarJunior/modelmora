"""US1 acceptance scenarios 1-6 and SC-001 (spec.md), against stand-in models."""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient

from modelmora.api.app import AppState, create_app
from modelmora.api.requests import RequestStore
from modelmora.config import Config
from modelmora.registry.defaults import ModelRegistry
from modelmora.runners.base import Runner
from modelmora.runners.standin import StandInTextRunner
from tests.conftest import CALLER_TOKEN, TEXT_MODEL, VISION_MODEL


def _submit_text(client: TestClient, **body_overrides: object):
    body: dict[str, object] = {"kind": "text", "instructions": "Write a short artist statement."}
    body.update(body_overrides)
    return client.post("/modelmora/v1/requests", json=body)


def _poll(client: TestClient, request_id: str) -> dict[str, Any]:
    response = client.get(f"/modelmora/v1/requests/{request_id}")
    assert response.status_code == 200
    return response.json()  # type: ignore[no-any-return]


def test_default_model_resolution(client: TestClient) -> None:
    """Scenario 1: no model named -> the default text model serves it, loading itself."""
    response = _submit_text(client)
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["model"] == {"name": TEXT_MODEL.name, "version": TEXT_MODEL.version}

    status = _poll(client, accepted["requestId"])
    assert status["state"] == "done"
    assert status["result"]["model"] == accepted["model"]
    assert TEXT_MODEL.name in status["result"]["text"]


def test_named_model_is_honored(client: TestClient) -> None:
    """Scenario 2: naming a model on record serves it from that model."""
    response = _submit_text(
        client, model={"name": VISION_MODEL.name, "version": VISION_MODEL.version}
    )
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["model"] == {"name": VISION_MODEL.name, "version": VISION_MODEL.version}

    status = _poll(client, accepted["requestId"])
    assert VISION_MODEL.name in status["result"]["text"]


def test_unknown_model_is_refused_with_no_substitute(client: TestClient) -> None:
    """Scenario 3: naming a model not on record refuses, and nothing substitutes it."""
    response = _submit_text(client, model={"name": "not-on-record", "version": "9"})
    assert response.status_code == 404
    assert response.json()["reason"] == "unknown_model"


def test_images_are_read_by_the_default_image_capable_model(client: TestClient) -> None:
    """Scenario 4: an image with a question is answered by a model that reads images."""
    response = _submit_text(
        client,
        instructions="describe what this shows",
        images=[{"mediaType": "image/png", "base64": "aGVsbG8="}],
    )
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["model"] == {"name": VISION_MODEL.name, "version": VISION_MODEL.version}

    status = _poll(client, accepted["requestId"])
    assert "image" in status["result"]["text"].lower()


def test_images_refused_when_no_model_on_record_reads_them() -> None:
    """Scenario 5: no image-reading text model on record -> invalid_request."""
    registry = ModelRegistry()
    registry.register(TEXT_MODEL, default_for=["text"])
    runners: dict[tuple[str, str], Runner] = {
        (TEXT_MODEL.name, TEXT_MODEL.version): StandInTextRunner(
            name=TEXT_MODEL.name, version=TEXT_MODEL.version
        )
    }
    state = AppState(
        config=Config(caller_tokens={CALLER_TOKEN: "sonavida"}),
        registry=registry,
        runners=runners,
        store=RequestStore(),
    )
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    response = _submit_text(client, images=[{"mediaType": "image/png", "base64": "aGVsbG8="}])
    assert response.status_code == 400
    body = response.json()
    assert body["reason"] == "invalid_request"
    assert "image" in body["detail"].lower()


def test_same_seed_and_length_reproduce_the_same_text(client: TestClient) -> None:
    """Scenario 6: same model, version, seed and length limit -> identical text."""
    body = {
        "kind": "text",
        "instructions": "Write a short artist statement.",
        "settings": {"seed": 42, "maxLength": 100},
    }
    first = client.post("/modelmora/v1/requests", json=body).json()
    second = client.post("/modelmora/v1/requests", json=body).json()

    first_status = _poll(client, first["requestId"])
    second_status = _poll(client, second["requestId"])
    assert first_status["result"]["text"] == second_status["result"]["text"]
