"""Shared helpers for the queue test suite (T027-T036).

Unlike `tests/conftest.py`'s single `state`/`client` pair, these tests each need a
line small enough, or models slow enough, to force the behavior under test -- so each
builds its own `AppState` through `build_queue_state` rather than sharing one.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

import pytest
from starlette.testclient import TestClient

from modelmora.api.app import create_app
from modelmora.api.requests import RequestStore
from modelmora.api.state import AppState
from modelmora.config import Config
from modelmora.queue.line import Line
from modelmora.registry.registry import ModelRegistry, RegisteredModel
from modelmora.runners.standin import StandInImageRunner, StandInTextRunner
from modelmora.worker.holding import ImageHoldingStore
from modelmora.worker.residency import Residency

CALLER_TOKEN = "sonavida-test-token"
CALLER_NAME = "sonavida"
OTHER_TOKEN = "curagusta-test-token"
OTHER_NAME = "curagusta"
THIRD_TOKEN = "descridiva-test-token"
THIRD_NAME = "descridiva"
FOURTH_TOKEN = "museumusa-test-token"
FOURTH_NAME = "museumusa"

ALL_CALLERS = {
    CALLER_TOKEN: CALLER_NAME,
    OTHER_TOKEN: OTHER_NAME,
    THIRD_TOKEN: THIRD_NAME,
    FOURTH_TOKEN: FOURTH_NAME,
}


def build_queue_state(
    *,
    line_limit: int = 32,
    overtaking_seconds: float = 120,
    idle_unload_seconds: float = 600,
    capacity_bytes: int | None = None,
) -> AppState:
    """An otherwise-empty AppState: tests add their own models (`add_text_model` etc.)."""
    config = Config(
        overtaking_seconds=int(overtaking_seconds),
        idle_unload_seconds=int(idle_unload_seconds),
        caller_tokens=dict(ALL_CALLERS),
    )
    residency = Residency(capacity_bytes=capacity_bytes) if capacity_bytes else Residency()
    return AppState(
        config=config,
        registry=ModelRegistry(),
        runners={},
        store=RequestStore(),
        residency=residency,
        holding=ImageHoldingStore(),
        line=Line(limit=line_limit),
    )


def add_text_model(
    state: AppState,
    name: str,
    *,
    fake_load_seconds: float = 0.0,
    fake_footprint_bytes: int = 256 * 1024 * 1024,
    reads_images: bool = False,
    default: bool = True,
) -> RegisteredModel:
    model = RegisteredModel(
        name=name,
        version="1.0",
        kind="text",
        reads_images=reads_images,
        license="Synthetic-Test-License",
    )
    state.registry.register(model, default_for=["text"] if default else [])
    state.runners[(model.name, model.version)] = StandInTextRunner(
        name=model.name,
        version=model.version,
        reads_images=reads_images,
        fake_load_seconds=fake_load_seconds,
        fake_footprint_bytes=fake_footprint_bytes,
    )
    return model


def add_image_model(
    state: AppState,
    name: str,
    *,
    fake_load_seconds: float = 0.0,
    fake_footprint_bytes: int = 512 * 1024 * 1024,
    default: bool = True,
) -> RegisteredModel:
    model = RegisteredModel(
        name=name,
        version="1.0",
        kind="image",
        reads_images=False,
        license="Synthetic-Test-License",
    )
    state.registry.register(model, default_for=["image"] if default else [])
    state.runners[(model.name, model.version)] = StandInImageRunner(
        name=model.name,
        version=model.version,
        fake_load_seconds=fake_load_seconds,
        fake_footprint_bytes=fake_footprint_bytes,
    )
    return model


@pytest.fixture
def make_client() -> Iterator[Callable[[AppState], TestClient]]:
    """Wraps `state` in a running app and stops its worker once the test is done."""
    states: list[AppState] = []

    def _make(state: AppState, *, token: str = CALLER_TOKEN) -> TestClient:
        app = create_app(state)
        states.append(state)
        return TestClient(app, headers={"Authorization": f"Bearer {token}"})

    yield _make
    for state in states:
        if state.worker is not None:
            state.worker.stop(timeout=2.0)


def poll_status(client: TestClient, request_id: str, *, wait_seconds: int = 5) -> dict:
    """Long-polls for a terminal state (`RequestStore.wait_for_change`, T035)."""
    response = client.get(
        f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": wait_seconds}
    )
    assert response.status_code == 200
    return response.json()


def peek_status(client: TestClient, request_id: str) -> dict:
    """The current state, with no waiting."""
    response = client.get(f"/modelmora/v1/requests/{request_id}")
    assert response.status_code == 200
    return response.json()


def wait_until(
    predicate: Callable[[], bool], *, timeout: float = 5.0, interval: float = 0.01
) -> None:
    """Polls `predicate` until it is true, for assertions that need a mid-flight state."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout}s")
