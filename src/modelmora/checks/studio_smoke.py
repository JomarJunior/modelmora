"""The manual on-Studio check (T049, quickstart Scenario 7).

Real text and image models, a forced eviction, availability across the lifecycle, and
a clean shutdown that answers a request it could not wait for. Not part of CI: no
GPU-free stand-in can prove `torch.cuda` residency or a real eviction, so this is run
by hand on the Studio machine, with the `gpu` extra installed:

    uv run python -m modelmora.checks.studio_smoke

It points at two local model directories by default -- override with
`MODELMORA_SMOKE_TEXT_MODEL_PATH` and `MODELMORA_SMOKE_IMAGE_MODEL_PATH` if the Studio
keeps its weights somewhere else. It builds its own `AppState` with real runners wired
directly, the same way `cli.py`'s `_test_mode_registry` wires stand-ins for
`--test-mode`: `modelmora serve`'s own registry-to-runner wiring is a deliberate seam
(see the comment in `cli.py`), not yet closed by any task.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from typing import Any

from starlette.testclient import TestClient

from modelmora.api.app import create_app
from modelmora.api.availability import build_availability
from modelmora.api.lifecycle import shutdown
from modelmora.api.requests import RequestStore
from modelmora.api.state import AppState
from modelmora.config import Config
from modelmora.registry.registry import ModelRegistry
from modelmora.runners.image import ImageRunner
from modelmora.runners.text import TextRunner
from modelmora.worker.holding import ImageHoldingStore
from modelmora.worker.residency import Residency

CALLER_TOKEN = "studio-smoke-token"  # noqa: S105 -- a loopback-only test token, not a secret
CALLER_NAME = "studio-smoke"

TEXT_MODEL_NAME = "a small open text model"
IMAGE_MODEL_NAME = "a small open image model"

TEXT_MODEL_PATH = os.environ.get(
    "MODELMORA_SMOKE_TEXT_MODEL_PATH", "/data/modelmora-weights/a small open text model"
)
IMAGE_MODEL_PATH = os.environ.get(
    "MODELMORA_SMOKE_IMAGE_MODEL_PATH", "/data/modelmora-weights/a small open image model"
)


def _log(message: str) -> None:
    print(f"[studio_smoke] {message}")


def _measure_footprint_bytes(build_runner: Callable[[], TextRunner | ImageRunner]) -> int:
    """Builds and loads a throwaway runner just to learn its real footprint.

    `Residency.ensure_loaded` and `check_image_capability` both ask
    `declared_footprint_bytes()` *before* `load()` (FR-009, FR-011); a real runner
    only knows its true footprint once its weights are on the GPU. The runner built
    here is discarded -- the figure it measured is passed as the `declared_footprint_bytes`
    hint to the runner instances actually used below, so admission and eviction have a
    real number to reason about from the very first request, not only after it.
    """
    runner = build_runner()
    runner.load()
    footprint = runner.declared_footprint_bytes()
    runner.unload()
    return footprint


def _build_state(
    text_runner: TextRunner, image_runner: ImageRunner, capacity_bytes: int
) -> AppState:
    registry = (
        ModelRegistry()
    )  # in-memory: a smoke run leaves no trace in the Studio's own registry
    registry.add_model(
        name=text_runner.name,
        version=text_runner.version,
        kind="text",
        source="<model page>",
        weights_digest="sha256:studio-smoke-not-verified",  # T040's own check proves verify.py
        added_by=CALLER_NAME,
        license_name="Apache-2.0",
        license_source="<model page>",
        license_confirmed_by=CALLER_NAME,
        filter_disclosure="none",
    )
    registry.set_default("text", text_runner.name, text_runner.version)

    registry.add_model(
        name=image_runner.name,
        version=image_runner.version,
        kind="image",
        source="<model page>",
        weights_digest="sha256:studio-smoke-not-verified",
        added_by=CALLER_NAME,
        license_name="an open model licence",
        license_source="<model page>",
        license_confirmed_by=CALLER_NAME,
        # This repository ships no safety checker, and the runner loads none (R-2):
        # nothing to disclose.
        filter_disclosure="none",
    )
    registry.set_default("image", image_runner.name, image_runner.version)

    return AppState(
        config=Config(caller_tokens={CALLER_TOKEN: CALLER_NAME}),
        registry=registry,
        runners={
            (text_runner.name, text_runner.version): text_runner,
            (image_runner.name, image_runner.version): image_runner,
        },
        store=RequestStore(),
        residency=Residency(capacity_bytes=capacity_bytes),
        holding=ImageHoldingStore(),
    )


_MAX_WAIT_SECONDS = 30  # the contract's own cap on a single long poll (R-6)


def _poll_until_terminal(
    client: TestClient, request_id: str, *, timeout_seconds: float
) -> dict[str, Any]:
    """Repeats the 30-second long poll until a terminal state or `timeout_seconds`."""
    deadline = time.monotonic() + timeout_seconds
    body: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(
            f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": _MAX_WAIT_SECONDS}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        if body["state"] not in ("waiting", "running"):
            return body
    raise AssertionError(f"did not finish within {timeout_seconds}s: {body}")


def _peek(client: TestClient, request_id: str) -> dict[str, Any]:
    response = client.get(f"/modelmora/v1/requests/{request_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def main() -> int:
    _log(f"loading {TEXT_MODEL_NAME} once to measure its real footprint...")
    text_footprint = _measure_footprint_bytes(
        lambda: TextRunner(name=TEXT_MODEL_NAME, version="1", model_path=TEXT_MODEL_PATH)
    )
    _log(f"loading {IMAGE_MODEL_NAME} once to measure its real footprint...")
    image_footprint = _measure_footprint_bytes(
        lambda: ImageRunner(name=IMAGE_MODEL_NAME, version="1", model_path=IMAGE_MODEL_PATH)
    )
    _log(
        f"measured footprints: text={text_footprint / 1024**2:.0f} MiB, "
        f"image={image_footprint / 1024**2:.0f} MiB"
    )
    # Both models are small enough that a real 24GB Studio GPU would happily hold both
    # at once, which would prove nothing about eviction (US2 acceptance scenario 2).
    # A capacity just above the larger of the two, alone, forces exactly the room
    # contention the quickstart asks for.
    capacity_bytes = int(max(text_footprint, image_footprint) * 1.2)
    assert capacity_bytes < text_footprint + image_footprint, (
        "models are too small relative to each other for this capacity to force an eviction"
    )

    text_runner = TextRunner(
        name=TEXT_MODEL_NAME,
        version="1",
        model_path=TEXT_MODEL_PATH,
        declared_footprint_bytes=text_footprint,
    )
    image_runner = ImageRunner(
        name=IMAGE_MODEL_NAME,
        version="1",
        model_path=IMAGE_MODEL_PATH,
        declared_footprint_bytes=image_footprint,
    )
    state = _build_state(text_runner, image_runner, capacity_bytes)

    availability_before_start = build_availability(state)
    _log(f"availability before the worker starts: {availability_before_start.state}")
    assert availability_before_start.state == "starting", "US5 scenario 1"

    app = create_app(state)
    client = TestClient(app, headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    availability_running = build_availability(state)
    _log(
        f"availability once running: {availability_running.state}, "
        f"servable text={availability_running.servable.text} "
        f"image={availability_running.servable.image}"
    )
    assert availability_running.state == "running"
    assert availability_running.servable.text == 1
    assert availability_running.servable.image == 1

    _log("submitting a text request to the real text model...")
    started = time.monotonic()
    text_submit = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "In one sentence, describe an empty gallery at dawn.",
        },
    )
    assert text_submit.status_code == 202, text_submit.text
    text_status = _poll_until_terminal(client, text_submit.json()["requestId"], timeout_seconds=120)
    text_elapsed = time.monotonic() - started
    _log(f"text result in {text_elapsed:.1f}s: {text_status['result']['text']!r}")
    assert text_status["state"] == "done"
    assert text_status["result"]["model"]["name"] == TEXT_MODEL_NAME
    assert text_runner.is_loaded()

    _log("submitting an image request -- expect the text model to be evicted...")
    started = time.monotonic()
    image_submit = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "image",
            "description": "A quiet museum gallery at dawn, soft light, no figures.",
            "size": {"width": 384, "height": 384},
            "settings": {"seed": 7, "steps": 20},
        },
    )
    assert image_submit.status_code == 202, image_submit.text
    image_status = _poll_until_terminal(
        client, image_submit.json()["requestId"], timeout_seconds=180
    )
    image_elapsed = time.monotonic() - started
    _log(
        f"image result in {image_elapsed:.1f}s, "
        f"settingsUsed={image_status['result']['settingsUsed']}"
    )
    assert image_status["state"] == "done"
    assert image_runner.is_loaded()
    assert not text_runner.is_loaded(), "the text model was not evicted to make room (FR-009)"

    image_bytes = client.get(f"/modelmora/v1/requests/{image_submit.json()['requestId']}/image")
    assert image_bytes.status_code == 200
    _log(f"fetched {len(image_bytes.content)} bytes of PNG, never an error about memory")

    _log("submitting one more text request, then stopping immediately without waiting...")
    late_submit = client.post(
        "/modelmora/v1/requests",
        json={"kind": "text", "instructions": "One more sentence, about closing time."},
    )
    assert late_submit.status_code == 202, late_submit.text
    shutdown(state)
    late_status = _peek(client, late_submit.json()["requestId"])
    _log(f"the request left open at shutdown ended: {late_status['state']}")
    assert late_status["state"] == "stopped_before_completion", (
        "US5 scenario 2, SC-009: nothing may be left open on shutdown"
    )

    availability_stopped = build_availability(state)
    _log(f"availability after stopping: {availability_stopped.state}")
    assert availability_stopped.state == "stopping"

    _log("all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
