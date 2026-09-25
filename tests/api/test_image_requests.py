"""Asking for an image and getting it back (T022).

US2 acceptance scenarios 1 to 3, and SC-001 for images: a caller names at most a model
and never loads or places one. Everything here runs on the stand-in image runner, so no
GPU is involved; the real `diffusers` runner is T023, verifiable only on the Studio.

Generation happens on the background worker (T032), not inline with the POST, so a
status check right after submitting polls with `waitSeconds` instead of assuming the
result is already there.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image
from starlette.testclient import TestClient

from modelmora.api.app import AppState, create_app
from modelmora.registry.registry import RegisteredModel
from modelmora.runners.standin import StandInImageRunner
from tests.conftest import CALLER_TOKEN, IMAGE_MODEL, TEXT_MODEL, build_state

A_SIZE = {"width": 256, "height": 192}


def _submit(client: TestClient, **overrides: object) -> dict:
    body: dict[str, object] = {
        "kind": "image",
        "description": "Low tide at dusk, no figures.",
        "size": A_SIZE,
    }
    body.update(overrides)
    response = client.post("/modelmora/v1/requests", json=body)
    return {"status": response.status_code, "body": response.json()}


def _poll(client: TestClient, request_id: str) -> dict:
    # Generation runs on the background worker (T032); the long poll waits for it
    # to reach a terminal state instead of racing it.
    response = client.get(f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": 5})
    assert response.status_code == 200
    return response.json()


def test_an_image_comes_back_with_its_model_seed_and_settings(client: TestClient) -> None:
    """US2 acceptance scenario 1, and SC-001: no model named, nothing loaded by the caller."""
    submitted = _submit(client, settings={"seed": 7, "steps": 12})

    assert submitted["status"] == 202
    assert submitted["body"]["model"]["name"] == IMAGE_MODEL.name
    request_id = submitted["body"]["requestId"]

    status = _poll(client, request_id)
    assert status["state"] == "done"
    result = status["result"]
    assert result["model"] == {"name": IMAGE_MODEL.name, "version": IMAGE_MODEL.version}
    assert result["imageAvailable"] is True
    assert result["settingsUsed"]["seed"] == 7
    assert result["settingsUsed"]["steps"] == 12
    assert result["text"] is None

    image_response = client.get(f"/modelmora/v1/requests/{request_id}/image")
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(image_response.content)) as image:
        assert image.size == (A_SIZE["width"], A_SIZE["height"])


def test_the_same_seed_reproduces_the_same_image(client: TestClient) -> None:
    """FR-006: same model, same request, same seed, same result."""
    first = _submit(client, settings={"seed": 42, "steps": 8})
    second = _submit(client, settings={"seed": 42, "steps": 8})
    _poll(client, first["body"]["requestId"])
    _poll(client, second["body"]["requestId"])

    first_bytes = client.get(f"/modelmora/v1/requests/{first['body']['requestId']}/image").content
    second_bytes = client.get(f"/modelmora/v1/requests/{second['body']['requestId']}/image").content

    assert first_bytes == second_bytes


def test_a_text_model_is_evicted_to_make_room_and_the_caller_only_waits(
    state: AppState, client: TestClient
) -> None:
    """US2 acceptance scenario 2: no caller ever sees a memory error (FR-009)."""
    text_runner = state.runners[(TEXT_MODEL.name, TEXT_MODEL.version)]
    image_runner = state.runners[(IMAGE_MODEL.name, IMAGE_MODEL.version)]

    # Fill the GPU: the text model alone leaves no room beside the image model.
    state.residency = type(state.residency)(capacity_bytes=image_runner.declared_footprint_bytes())
    first = client.post("/modelmora/v1/requests", json={"kind": "text", "instructions": "first"})
    _poll(client, first.json()["requestId"])
    assert text_runner.is_loaded()

    submitted = _submit(client)

    assert submitted["status"] == 202, "an image request saw an error instead of a wait"
    status = _poll(client, submitted["body"]["requestId"])
    assert status["state"] == "done"
    assert status["failure"] is None
    assert image_runner.is_loaded()
    assert not text_runner.is_loaded(), "the text model was not evicted to make room"


def test_a_size_the_model_cannot_produce_is_refused_before_queueing() -> None:
    """US2 acceptance scenario 3: refused with a reason that names the problem."""
    state = build_state()
    small = RegisteredModel(
        name="synthetic-image-tiny",
        version="1.0",
        kind="image",
        reads_images=False,
        license="Synthetic-Test-License",
    )
    state.registry.register(small, default_for=["image"])
    state.runners[(small.name, small.version)] = StandInImageRunner(
        name=small.name, version=small.version, max_width=512, max_height=512
    )
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    submitted = _submit(client, size={"width": 2048, "height": 2048})

    assert submitted["status"] == 400
    assert submitted["body"]["reason"] == "invalid_request"
    assert "512x512" in submitted["body"]["detail"]
    assert "2048x2048" in submitted["body"]["detail"]


def test_a_model_too_large_for_this_studio_is_refused_at_once() -> None:
    """Never queued forever: refused as `cannot_be_served_on_this_studio` (Edge Cases)."""
    state = build_state()
    huge = RegisteredModel(
        name="synthetic-image-huge",
        version="1.0",
        kind="image",
        reads_images=False,
        license="Synthetic-Test-License",
    )
    state.registry.register(huge, default_for=["image"])
    state.runners[(huge.name, huge.version)] = StandInImageRunner(
        name=huge.name, version=huge.version, fake_footprint_bytes=64 * 1024**3
    )
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    submitted = _submit(client)

    assert submitted["body"]["reason"] == "cannot_be_served_on_this_studio"


def test_an_unknown_image_model_is_refused_with_no_substitute(client: TestClient) -> None:
    """FR-004 and FR-007: a named model is served or refused, never swapped."""
    submitted = _submit(client, model={"name": "no-such-model", "version": "9.9"})

    assert submitted["body"]["reason"] == "unknown_model"


@pytest.mark.parametrize("bad_size", [{"width": 8, "height": 256}, {"width": 256, "height": 9000}])
def test_a_size_outside_the_contract_is_refused(client: TestClient, bad_size: dict) -> None:
    """The contract bounds width and height to 64-4096."""
    submitted = _submit(client, size=bad_size)

    assert submitted["status"] == 400
    assert submitted["body"]["reason"] == "invalid_request"
