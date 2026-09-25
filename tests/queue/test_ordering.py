"""T028: arrival order, bounded overtaking, and no dependence on caller or persona
(FR-019, SC-010).

`pick_next` is tested directly for the exact bound math (deterministic, no threads);
one end-to-end test through the real API and worker confirms the qualitative behavior
acceptance scenario 5 describes.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta

from modelmora.messages import ModelRef
from modelmora.queue.line import QueuedRequest
from modelmora.queue.ordering import pick_next
from tests.queue.conftest import add_text_model, build_queue_state, peek_status, wait_until

MODEL_A = ModelRef(name="model-a", version="1.0")
MODEL_B = ModelRef(name="model-b", version="1.0")


def _request(model: ModelRef, *, caller: str, submitted_at: datetime) -> QueuedRequest:
    return QueuedRequest(
        request_id=uuid.uuid4(),
        caller=caller,
        kind="text",
        model=model,
        runner=object(),  # type: ignore[arg-type]
        submitted_at=submitted_at,
        generate=lambda: None,  # type: ignore[arg-type,return-value]
    )


def test_arrival_order_holds_when_nothing_is_resident() -> None:
    now = datetime.now(UTC)
    older = _request(MODEL_A, caller="sonavida", submitted_at=now - timedelta(seconds=5))
    newer = _request(MODEL_B, caller="curagusta", submitted_at=now)

    assert pick_next([older, newer], resident_keys=set(), overtaking_seconds=120, now=now) is older


def test_a_resident_model_may_run_ahead_of_an_older_load() -> None:
    now = datetime.now(UTC)
    older_needs_load = _request(MODEL_A, caller="sonavida", submitted_at=now - timedelta(seconds=5))
    newer_resident = _request(MODEL_B, caller="sonavida", submitted_at=now)

    chosen = pick_next(
        [older_needs_load, newer_resident],
        resident_keys={("model-b", "1.0")},
        overtaking_seconds=120,
        now=now,
    )

    assert chosen is newer_resident


def test_no_request_is_overtaken_past_the_bound() -> None:
    now = datetime.now(UTC)
    overtaken_too_long = _request(
        MODEL_A, caller="sonavida", submitted_at=now - timedelta(seconds=121)
    )
    newer_resident = _request(MODEL_B, caller="sonavida", submitted_at=now)

    chosen = pick_next(
        [overtaken_too_long, newer_resident],
        resident_keys={("model-b", "1.0")},
        overtaking_seconds=120,
        now=now,
    )

    assert chosen is overtaken_too_long


def test_ordering_does_not_depend_on_the_caller_or_persona() -> None:
    """Swapping which caller owns which request changes nothing about the outcome."""
    now = datetime.now(UTC)
    for older_caller, newer_caller in [("sonavida", "curagusta"), ("curagusta", "sonavida")]:
        older = _request(MODEL_A, caller=older_caller, submitted_at=now - timedelta(seconds=5))
        newer = _request(MODEL_B, caller=newer_caller, submitted_at=now)

        chosen = pick_next(
            [older, newer], resident_keys={("model-b", "1.0")}, overtaking_seconds=120, now=now
        )

        assert chosen is newer, "the resident model won regardless of who asked for what"


def test_end_to_end_a_resident_model_runs_ahead_of_an_older_load(make_client) -> None:
    """US3 acceptance scenario 5, through the real API, line and worker."""
    state = build_queue_state(line_limit=10, overtaking_seconds=60)
    model_a = add_text_model(state, "synthetic-text-ordering-a", fake_load_seconds=0.0)
    model_b = add_text_model(
        state, "synthetic-text-ordering-b", fake_load_seconds=0.3, default=False
    )
    runner_a = state.runners[(model_a.name, model_a.version)]

    # Occupies the worker (and makes A resident) while B1 and A2 are both queued, so
    # they genuinely compete for what runs next rather than being served one at a time.
    gate = threading.Event()
    original = runner_a.generate_text

    def gated(**kwargs: object):  # type: ignore[no-untyped-def]
        gate.wait()
        return original(**kwargs)  # type: ignore[arg-type]

    runner_a.generate_text = gated  # type: ignore[method-assign]
    client = make_client(state)

    spacer = client.post("/modelmora/v1/requests", json={"kind": "text", "instructions": "spacer"})
    assert spacer.status_code == 202

    b1 = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "older, needs a load",
            "model": {"name": model_b.name, "version": model_b.version},
        },
    )
    a2 = client.post(
        "/modelmora/v1/requests",
        json={
            "kind": "text",
            "instructions": "newer, already resident",
            "model": {"name": model_a.name, "version": model_a.version},
        },
    )
    assert b1.status_code == 202 and a2.status_code == 202

    gate.set()  # release the spacer; the worker must now choose between b1 and a2

    def b1_is_running() -> bool:
        return peek_status(client, b1.json()["requestId"])["state"] == "running"

    wait_until(b1_is_running, timeout=5.0)

    # b1 needed a real load (0.3s); if a2 had not been run first, it could not
    # possibly be "done" yet at the exact moment b1 starts.
    assert peek_status(client, a2.json()["requestId"])["state"] == "done"
