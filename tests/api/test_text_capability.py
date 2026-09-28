"""A conversation that could never fit a model's context window is refused before
queueing (T065, FR-007, FR-011), rather than accepted and left to fail or be
silently truncated mid-generation. Proven with a stand-in given a fixed context
window (FR-033) -- no real `.gguf` model needed.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from modelmora.api.app import create_app
from modelmora.registry.registry import RegisteredModel
from modelmora.runners.standin import StandInTextRunner
from tests.conftest import CALLER_TOKEN, build_state


class _FixedContextStandIn(StandInTextRunner):
    def __init__(self, *, context_window: int, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._context_window = context_window

    def context_window_tokens(self) -> int | None:
        return self._context_window


def _client_with_small_context_model(context_window: int) -> TestClient:
    state = build_state()
    model = RegisteredModel(
        name="synthetic-small-context",
        version="1.0",
        kind="text",
        reads_images=False,
        license="Synthetic-Test-License",
    )
    state.registry.register(model, default_for=["text"])
    state.runners[(model.name, model.version)] = _FixedContextStandIn(
        name=model.name, version=model.version, context_window=context_window
    )
    return TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})


def test_a_request_that_cannot_fit_the_context_window_is_refused_before_queueing() -> None:
    client = _client_with_small_context_model(context_window=16)

    response = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "a" * 2000,  # far more than 16 tokens' worth of chars
            "settings": {"maxLength": 200},
        },
    )

    assert response.status_code == 400
    assert response.json()["reason"] == "invalid_request"
    assert "context window" in response.json()["detail"]


def test_a_request_that_fits_the_context_window_is_accepted() -> None:
    client = _client_with_small_context_model(context_window=8000)

    response = client.post(
        "/modelmora/v1/requests",
        json={"kind": "text", "instructions": "a short one", "settings": {"maxLength": 40}},
    )

    assert response.status_code == 202


def test_a_runner_with_no_fixed_context_window_is_never_refused_on_this_ground() -> None:
    """The stand-ins and `TextRunner` (`transformers`) declare no window at all --
    `context_window_tokens()` defaults to `None`, so this check never fires for them.
    """
    state = build_state()
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    response = client.post(
        "/modelmora/v1/requests",
        json={"kind": "text", "instructions": "a" * 5000, "settings": {"maxLength": 30000}},
    )

    assert response.status_code == 202
