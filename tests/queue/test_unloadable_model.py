"""T072: a model that cannot be loaded at all (spec Edge Cases, FR-011, FR-022).

"Files missing, damaged or changed: requests for it are refused with 'model
unavailable', the team is told, and no other model is used in its place." A load
failure is not a generation failure: the accepted request that found it ends
`model_unavailable`, the operator log carries one WARNING line naming the model, and
every later request for that model is refused before it is queued, rather than
accepted only to retry a load already known to fail. No GPU: the failing load is a
stand-in's.
"""

from __future__ import annotations

import logging

import pytest

from tests.queue.conftest import add_text_model, build_queue_state, poll_status

MARKER = "synthetic-marker-7c1e-unloadable"


def _body(model_name: str) -> dict:
    return {
        "kind": "text",
        "instructions": f"Describe an empty gallery. {MARKER}",
        "model": {"name": model_name, "version": "1.0"},
    }


def _break_load(state, model) -> list[str]:  # type: ignore[no-untyped-def]
    runner = state.runners[(model.name, model.version)]
    attempts: list[str] = []

    def failing_load() -> None:
        attempts.append("load")
        raise RuntimeError("weights could not be read")

    runner.load = failing_load  # type: ignore[method-assign]
    return attempts


def test_a_load_failure_ends_the_request_model_unavailable_and_tells_the_team(
    make_client, caplog: pytest.LogCaptureFixture
) -> None:
    state = build_queue_state(line_limit=10)
    broken = add_text_model(state, "synthetic-text-unloadable")
    _break_load(state, broken)
    client = make_client(state)

    with caplog.at_level(logging.WARNING):
        accepted = client.post("/modelmora/v1/requests", json=_body(broken.name))
        assert accepted.status_code == 202
        status = poll_status(client, accepted.json()["requestId"])

    assert status["state"] == "failed"
    assert status["failure"]["reason"] == "model_unavailable"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(broken.name in r.getMessage() for r in warnings), "the team was not told"
    assert all(MARKER not in r.getMessage() for r in caplog.records), "content reached a log"


def test_later_requests_for_an_unloadable_model_are_refused_before_queueing(
    make_client,
) -> None:
    state = build_queue_state(line_limit=10)
    broken = add_text_model(state, "synthetic-text-unloadable-again")
    attempts = _break_load(state, broken)
    client = make_client(state)

    first = client.post("/modelmora/v1/requests", json=_body(broken.name))
    poll_status(client, first.json()["requestId"])

    second = client.post("/modelmora/v1/requests", json=_body(broken.name))

    assert second.status_code != 202, "accepted only to retry a load known to fail"
    assert second.json()["reason"] == "model_unavailable"
    assert attempts == ["load"], "the failed load was retried"


def test_an_unloadable_model_leaves_other_models_serving(make_client) -> None:
    state = build_queue_state(line_limit=10)
    good = add_text_model(state, "synthetic-text-loadable")
    broken = add_text_model(state, "synthetic-text-unloadable-beside", default=False)
    _break_load(state, broken)
    client = make_client(state)

    failing = client.post("/modelmora/v1/requests", json=_body(broken.name))
    working = client.post("/modelmora/v1/requests", json=_body(good.name))

    assert poll_status(client, failing.json()["requestId"])["state"] == "failed"
    working_status = poll_status(client, working.json()["requestId"])
    assert working_status["state"] == "done"
    assert working_status["result"]["model"]["name"] == good.name, "a substitute was used"
