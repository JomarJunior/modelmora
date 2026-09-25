"""US5 acceptance scenarios 1 and 3, plus the empty-registry Edge Case (T044).

`starting` before models are ready is not a failure (scenario 1); `running` reports
servable counts and the queue length, and nothing beyond that about other callers'
requests (scenario 3); an empty registry reports zero servable, and a request against
it is refused `model_unavailable`, never a service failure (Edge Cases). No GPU: every
check here is against `AppState`/`build_availability` directly or through stand-ins.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from modelmora.api import requests as requests_api
from modelmora.api.availability import build_availability
from modelmora.api.requests import RequestStore
from modelmora.api.state import AppState
from modelmora.config import Config
from modelmora.messages import TextRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.registry import ModelRegistry
from modelmora.worker.holding import ImageHoldingStore
from modelmora.worker.residency import Residency
from tests.conftest import CALLER_NAME, CALLER_TOKEN, build_state


def test_starting_is_not_a_failure() -> None:
    """US5 scenario 1: no model is ready yet, so availability says 'starting', not
    'failed', and a submission is refused with a reason a caller can wait on."""
    state = build_state()
    assert state.lifecycle.state == "starting"

    availability = build_availability(state)
    assert availability.state == "starting"

    with pytest.raises(ModelMoraRefusal) as exc_info:
        requests_api.submit_text_request(
            state=state,
            caller=CALLER_NAME,
            request=TextRequest(kind="text", instructions="hello, is anyone there?"),
        )
    assert exc_info.value.reason == "starting"
    assert exc_info.value.retry_after_seconds is not None
    assert exc_info.value.retry_after_seconds > 0


def test_running_reports_servable_counts_and_queue_length_only(client: TestClient) -> None:
    """US5 scenario 3: what it can serve and the length of the line -- nothing else."""
    response = client.get("/modelmora/v1/availability")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "running"
    assert body["servable"] == {"text": 2, "image": 1}  # TEXT_MODEL, VISION_MODEL, IMAGE_MODEL
    assert body["queueLength"] == 0
    # The contract's Availability schema forbids extra fields (messages.py
    # ClosedModel); the closed key set is itself the proof nothing about another
    # caller's requests can ride along (FR-017).
    assert set(body.keys()) == {"state", "queueLength", "servable"}


def test_an_empty_registry_reports_zero_and_refuses_rather_than_fails() -> None:
    """spec Edge Cases: 'the registry is empty' -- told no model is available, not
    that the service failed."""
    state = AppState(
        config=Config(caller_tokens={CALLER_TOKEN: CALLER_NAME}),
        registry=ModelRegistry(),
        runners={},
        store=RequestStore(),
        residency=Residency(),
        holding=ImageHoldingStore(),
    )
    state.lifecycle.mark_ready()

    availability = build_availability(state)
    assert availability.servable.text == 0
    assert availability.servable.image == 0

    with pytest.raises(ModelMoraRefusal) as exc_info:
        requests_api.submit_text_request(
            state=state, caller=CALLER_NAME, request=TextRequest(kind="text", instructions="hi")
        )
    assert exc_info.value.reason == "model_unavailable"


def test_stopping_is_reported_and_refuses_new_work() -> None:
    """The third lifecycle state: FR-011's `stopping` reason exists for this."""
    state = build_state()
    state.lifecycle.mark_ready()
    state.lifecycle.begin_stopping()

    assert build_availability(state).state == "stopping"

    with pytest.raises(ModelMoraRefusal) as exc_info:
        requests_api.submit_text_request(
            state=state,
            caller=CALLER_NAME,
            request=TextRequest(kind="text", instructions="are you still there?"),
        )
    assert exc_info.value.reason == "stopping"
    assert exc_info.value.retry_after_seconds is not None
