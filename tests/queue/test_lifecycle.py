"""T029: every accepted request ends in exactly one terminal state (FR-013, FR-014,
Edge Cases).

`stopped_before_completion` is Phase 7's job (T045/T046, graceful shutdown); this
covers the three terminal states Phase 5 can produce on its own: done, failed and
withdrawn.
"""

from __future__ import annotations

import threading

from tests.queue.conftest import add_text_model, build_queue_state, peek_status, poll_status

TEXT_BODY = {"kind": "text", "instructions": "Write a short artist statement."}


def test_a_waiting_request_that_is_withdrawn_never_runs(make_client) -> None:
    state = build_queue_state(line_limit=10)
    model = add_text_model(state, "synthetic-text-lifecycle-withdraw")
    runner = state.runners[(model.name, model.version)]
    calls: list[str] = []
    original = runner.generate_text
    gate = threading.Event()

    def gated_and_counted(**kwargs: object):  # type: ignore[no-untyped-def]
        calls.append("ran")
        gate.wait()
        return original(**kwargs)  # type: ignore[arg-type]

    runner.generate_text = gated_and_counted  # type: ignore[method-assign]
    client = make_client(state)

    spacer = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    to_withdraw = client.post("/modelmora/v1/requests", json=TEXT_BODY)
    assert spacer.status_code == 202 and to_withdraw.status_code == 202

    withdrawal = client.delete(f"/modelmora/v1/requests/{to_withdraw.json()['requestId']}")
    assert withdrawal.status_code == 200
    assert withdrawal.json()["state"] == "withdrawn"

    gate.set()
    poll_status(client, spacer.json()["requestId"])

    final = peek_status(client, to_withdraw.json()["requestId"])
    assert final["state"] == "withdrawn"
    assert calls == ["ran"], "a withdrawn request still generated"


def test_a_running_request_that_fails_leaves_others_untouched(make_client) -> None:
    state = build_queue_state(line_limit=10)
    good_model = add_text_model(state, "synthetic-text-lifecycle-good")
    failing_model = add_text_model(state, "synthetic-text-lifecycle-failing", default=False)
    failing_runner = state.runners[(failing_model.name, failing_model.version)]
    attempts = 0

    def always_fails(**kwargs: object):  # type: ignore[no-untyped-def]
        nonlocal attempts
        attempts += 1
        raise RuntimeError("the model backend broke")

    failing_runner.generate_text = always_fails  # type: ignore[method-assign]
    client = make_client(state)

    failing = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "this will fail",
            "model": {"name": failing_model.name, "version": failing_model.version},
        },
    )
    good = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "this should still work",
            "model": {"name": good_model.name, "version": good_model.version},
        },
    )
    assert failing.status_code == 202 and good.status_code == 202

    failing_status = poll_status(client, failing.json()["requestId"])
    good_status = poll_status(client, good.json()["requestId"])

    assert failing_status["state"] == "failed"
    assert failing_status["failure"]["reason"] == "failed_during_generation"
    assert good_status["state"] == "done", "a failure elsewhere left another request unresolved"
    assert attempts == 1, "a failed request must not be silently retried with lower settings"


def test_every_accepted_request_ends_in_exactly_one_terminal_state(make_client) -> None:
    state = build_queue_state(line_limit=10)
    add_text_model(state, "synthetic-text-lifecycle-terminal")
    client = make_client(state)

    accepted = [client.post("/modelmora/v1/requests", json=TEXT_BODY) for _ in range(5)]
    terminal_states = {poll_status(client, a.json()["requestId"])["state"] for a in accepted}

    assert terminal_states <= {"done", "failed", "withdrawn", "stopped_before_completion"}
    assert all(poll_status(client, a.json()["requestId"])["state"] != "waiting" for a in accepted)
