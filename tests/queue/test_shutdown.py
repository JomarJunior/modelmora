"""On stop, every waiting or running request ends `stopped_before_completion`, and
nothing is left without a final answer (T045, FR-029, SC-009).

No GPU: a gated stand-in text runner (the same pattern as `test_admission.py`) keeps
one request genuinely `running` -- past `on_running`, blocked inside `generate_text` --
when shutdown is triggered, so the drain is exercised against a real mid-flight
request rather than a race that might already be `done`. `shutdown` joins the worker
thread (api/lifecycle.py), so the gate is released from a timer just after `shutdown`
is called, matching how a real, bounded generation would finish on its own -- the
caller-visible answer is still set before that join even starts.
"""

from __future__ import annotations

import threading

from modelmora.api.lifecycle import shutdown
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
        # shutdown() joins the worker thread; releasing the gate right after it is
        # called lets that join return quickly instead of waiting out its timeout.
        threading.Timer(0.05, gate.set).start()
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
        gate.set()  # idempotent: in case shutdown()'s join already timed out


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
        threading.Timer(0.05, gate.set).start()
        shutdown(state)

        for request_id in waiting_ids:
            assert peek_status(client, request_id)["state"] == "stopped_before_completion"
    finally:
        gate.set()


def test_shutdown_unloads_every_resident_runner(make_client) -> None:
    """A runner left resident is not the OS's job to clean up (T061).

    A stand-in's `unload()` only ever flips a flag, but a runner managing its own
    subprocess (`LlamaCppTextRunner`) does not get killed just because this process
    exits -- discovered on the Studio as an orphaned `llama-server` still holding the
    GPU after a clean shutdown. `shutdown()` must call `unload()` on everything
    `Residency` still considers resident.
    """
    state = build_queue_state(line_limit=5)
    model = add_text_model(state, "synthetic-text-shutdown-unload")
    runner = state.runners[(model.name, model.version)]
    client = make_client(state)

    submitted = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    poll_status(client, submitted.json()["requestId"])  # let it finish and become resident
    assert runner.is_loaded()

    shutdown(state)

    assert not runner.is_loaded()
