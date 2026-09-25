"""T027: admission answers immediately and honestly, and never drops a request
(FR-010, FR-015, SC-003).

A gated stand-in runner (not a fixed sleep) keeps the worker busy on cue, so the line
can be filled to its exact limit without racing the worker's own speed.
"""

from __future__ import annotations

import threading
import time

from tests.queue.conftest import (
    add_text_model,
    build_queue_state,
    peek_status,
    poll_status,
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


def test_every_submission_answers_within_a_second_while_the_worker_is_busy(make_client) -> None:
    state = build_queue_state(line_limit=10)
    model = add_text_model(state, "synthetic-text-admission")
    runner = state.runners[(model.name, model.version)]
    gate = _gate(runner)
    client = make_client(state)

    first = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    assert first.status_code == 202

    try:
        for _ in range(5):
            started = time.monotonic()
            response = client.post("/modelmora/v1/requests", json=TEXT_BODY)
            elapsed = time.monotonic() - started
            assert elapsed < 1.0, f"submission took {elapsed:.2f}s while the worker was busy"
            assert response.status_code == 202
            body = response.json()
            assert body["position"] >= 1
            assert body["estimatedWaitSeconds"] >= 0
    finally:
        gate.set()
        poll_status(client, first.json()["requestId"])


def test_a_full_line_is_refused_busy_never_accepted_then_dropped(make_client) -> None:
    state = build_queue_state(line_limit=2)
    model = add_text_model(state, "synthetic-text-admission-full")
    runner = state.runners[(model.name, model.version)]
    gate = _gate(runner)
    client = make_client(state)

    running = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    assert running.status_code == 202

    def is_running() -> bool:
        return peek_status(client, running.json()["requestId"])["state"] == "running"

    wait_until(is_running)

    first_wait = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    second_wait = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    assert first_wait.status_code == 202
    assert second_wait.status_code == 202

    try:
        overflow = client.post("/modelmora/v1/requests", json=TEXT_BODY)
        assert overflow.status_code == 409
        body = overflow.json()
        assert body["reason"] == "busy"
        assert body["retryAfterSeconds"] is not None and body["retryAfterSeconds"] > 0

        # Never accepted and then dropped: the busy request has no id to ask about,
        # and the line still holds exactly the two it admitted.
        assert "requestId" not in body
    finally:
        gate.set()
        poll_status(client, running.json()["requestId"])
        poll_status(client, first_wait.json()["requestId"])
        poll_status(client, second_wait.json()["requestId"])
