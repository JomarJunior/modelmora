"""On stop, every waiting or running request ends `stopped_before_completion`, and
nothing is left without a final answer (T045, FR-029, SC-009).

No GPU: a gated stand-in text runner (the same pattern as `test_admission.py`) keeps
one request genuinely `running` -- past `on_running`, blocked inside `generate_text` --
when shutdown is triggered, so the drain is exercised against a real mid-flight
request rather than a race that might already be `done`.
"""

from __future__ import annotations

import threading

from modelmora.api.lifecycle import shutdown
from tests.queue.conftest import (
    add_text_model,
    build_queue_state,
    peek_status,
    wait_until,
)

TEXT_BODY = {"kind": "text", "instructions": "Write a short artist statement."}


def _gate(runner: object) -> threading.Event:
    """Blocks the runner's `generate_text` until the returned event is set."""
    gate = threading.Event()
    original = runner.generate_text  # type: ignore[attr-defined]

    def blocked(**kwargs: object) -> object:
        gate.wait()
        return original(**kwargs)

    runner.generate_text = blocked  # type: ignore[attr-defined]
    return gate


def test_shutdown_answers_every_waiting_and_running_request(make_client) -> None:
    state = build_queue_state(line_limit=5)
    model = add_text_model(state, "synthetic-text-shutdown")
    runner = state.runners[(model.name, model.version)]
    gate = _gate(runner)
    client = make_client(state)

    running = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    waiting = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    assert running.status_code == 202
    assert waiting.status_code == 202

    def is_running() -> bool:
        return peek_status(client, running.json()["requestId"])["state"] == "running"

    wait_until(is_running)
    assert peek_status(client, waiting.json()["requestId"])["state"] == "waiting"

    try:
        shutdown(state)

        running_status = peek_status(client, running.json()["requestId"])
        waiting_status = peek_status(client, waiting.json()["requestId"])
        assert running_status["state"] == "stopped_before_completion"
        assert waiting_status["state"] == "stopped_before_completion"
        assert running_status["failure"] is None
        assert running_status["result"] is None

        too_late = client.post("/modelmora/v1/requests", json=TEXT_BODY)
        assert too_late.status_code == 503
        assert too_late.json()["reason"] == "stopping"
        assert too_late.json()["retryAfterSeconds"] is not None
    finally:
        gate.set()  # let the blocked worker thread unwind so it does not outlive the test


def test_shutdown_drains_several_waiting_requests(make_client) -> None:
    """Not just one: every still-waiting request gets the same answer."""
    state = build_queue_state(line_limit=5)
    model = add_text_model(state, "synthetic-text-shutdown-many")
    runner = state.runners[(model.name, model.version)]
    gate = _gate(runner)
    client = make_client(state)

    running = client.post("/modelmora/v1/requests", json=TEXT_BODY)

    def is_running() -> bool:
        return peek_status(client, running.json()["requestId"])["state"] == "running"

    wait_until(is_running)

    waiting_ids = [
        client.post("/modelmora/v1/requests", json=TEXT_BODY).json()["requestId"] for _ in range(3)
    ]

    try:
        shutdown(state)

        for request_id in waiting_ids:
            assert peek_status(client, request_id)["state"] == "stopped_before_completion"
    finally:
        gate.set()
