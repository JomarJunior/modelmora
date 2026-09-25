"""T033a: once every model has run at least once, most requests start close to their
estimate (SC-004, FR-018).

"Start within 50%" is read as an honest upper bound: a request should not have to wait
much longer than it was told, though finishing sooner than promised is not a
violation. Estimates round up (`Estimator.estimate_wait_seconds`), which biases toward
this direction on purpose.
"""

from __future__ import annotations

import uuid

from tests.queue.conftest import (
    CALLER_NAME,
    add_image_model,
    add_text_model,
    build_queue_state,
    poll_status,
)


def test_at_least_90_percent_of_requests_start_within_50_percent_of_their_estimate(
    make_client,
) -> None:
    state = build_queue_state(line_limit=32, overtaking_seconds=120)
    text_a = add_text_model(state, "synthetic-text-estimate-a", fake_load_seconds=0.05)
    text_b = add_text_model(
        state, "synthetic-text-estimate-b", fake_load_seconds=0.08, default=False
    )
    image_a = add_image_model(state, "synthetic-image-estimate-a", fake_load_seconds=0.1)
    models = [text_a, text_b, image_a]
    client = make_client(state)

    def _body(model, index: int) -> dict:
        if model.kind == "text":
            return {
                "kind": "text",
                "instructions": f"warm up {index}",
                "model": {"name": model.name, "version": model.version},
            }
        return {
            "kind": "image",
            "description": f"warm up {index}",
            "size": {"width": 64, "height": 64},
            "model": {"name": model.name, "version": model.version},
        }

    # SC-004 is measured once every model has run at least once.
    for i, model in enumerate(models):
        warm = client.post("/modelmora/v1/requests", json=_body(model, i))
        assert warm.status_code == 202
        poll_status(client, warm.json()["requestId"])

    accepted = []
    for i in range(20):
        model = models[i % len(models)]
        response = client.post("/modelmora/v1/requests", json=_body(model, 100 + i))
        assert response.status_code == 202
        accepted.append(response.json())

    within_bound = 0
    for a in accepted:
        status = poll_status(client, a["requestId"], wait_seconds=10)
        assert status["state"] == "done"
        record = state.store.get(CALLER_NAME, uuid.UUID(a["requestId"]))
        assert record is not None and record.started_at is not None
        actual_wait = (record.started_at - record.submitted_at).total_seconds()
        estimate = a["estimatedWaitSeconds"]
        # A small epsilon absorbs scheduling jitter around a near-zero estimate.
        if actual_wait <= estimate * 1.5 + 0.05:
            within_bound += 1

    assert within_bound / len(accepted) >= 0.9, (
        f"only {within_bound}/{len(accepted)} requests started within 50% of their estimate"
    )
