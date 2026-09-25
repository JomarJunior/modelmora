"""T028a: a burst bigger than the GPU can hold at once still answers everyone
(SC-002, quickstart Scenario 2).

20 mixed text and image requests from 4 callers, for more models (3 text + 2 image)
than fit on the GPU together (capacity fits only two at a time): every request ends
with a result or an explained answer, and none is lost, duplicated or left open.
"""

from __future__ import annotations

from tests.queue.conftest import (
    ALL_CALLERS,
    add_image_model,
    add_text_model,
    build_queue_state,
    poll_status,
)

FOOTPRINT = 256 * 1024 * 1024


def test_a_burst_of_20_from_4_callers_all_resolve(make_client) -> None:
    state = build_queue_state(line_limit=32, capacity_bytes=FOOTPRINT * 2)
    text_models = [
        add_text_model(state, f"synthetic-text-burst-{i}", fake_footprint_bytes=FOOTPRINT)
        for i in range(3)
    ]
    image_models = [
        add_image_model(state, f"synthetic-image-burst-{i}", fake_footprint_bytes=FOOTPRINT)
        for i in range(2)
    ]
    clients = [make_client(state, token=token) for token in ALL_CALLERS]

    accepted = []
    for i in range(20):
        client = clients[i % len(clients)]
        if i % 2 == 0:
            model = text_models[i % len(text_models)]
            body = {
                "kind": "text",
                "instructions": f"request {i}",
                "model": {"name": model.name, "version": model.version},
            }
        else:
            model = image_models[i % len(image_models)]
            body = {
                "kind": "image",
                "description": f"request {i}",
                "size": {"width": 64, "height": 64},
                "model": {"name": model.name, "version": model.version},
            }
        response = client.post("/modelmora/v1/requests", json=body)
        assert response.status_code == 202, f"request {i} was not accepted: {response.json()}"
        accepted.append((client, response.json()))

    request_ids = {a["requestId"] for _, a in accepted}
    assert len(request_ids) == 20, "some request ids collided or were reused"

    for client, a in accepted:
        status = poll_status(client, a["requestId"], wait_seconds=10)
        assert status["state"] in ("done", "failed"), (
            f"request {a['requestId']} was left {status['state']!r}, neither a result "
            "nor an explained answer"
        )
        if status["state"] == "done":
            assert status["result"]["model"] == a["model"], "the result used a different model"
