"""T036: nothing is ever downgraded to relieve load (FR-007, SC-008).

Across a burst that forces contention (more models than fit on the GPU together),
every result carries exactly the model and settings its request asked for or was told
at acceptance -- never a smaller size, a shorter length, or a different model.
"""

from __future__ import annotations

from typing import Any

from tests.queue.conftest import add_image_model, add_text_model, build_queue_state, poll_status

FOOTPRINT = 256 * 1024 * 1024


def test_a_burst_under_contention_never_changes_what_was_asked_for(make_client) -> None:
    state = build_queue_state(line_limit=32, capacity_bytes=FOOTPRINT)
    text_a = add_text_model(
        state, "synthetic-text-no-degradation-a", fake_footprint_bytes=FOOTPRINT
    )
    text_b = add_text_model(
        state, "synthetic-text-no-degradation-b", fake_footprint_bytes=FOOTPRINT, default=False
    )
    image_a = add_image_model(
        state, "synthetic-image-no-degradation-a", fake_footprint_bytes=FOOTPRINT
    )
    client = make_client(state)

    requests = []
    for i in range(9):
        body: dict[str, Any]
        if i % 3 == 0:
            model = text_a
            body = {
                "kind": "text",
                "instructions": f"request {i}",
                "settings": {"seed": i, "maxLength": 40 + i},
                "model": {"name": text_a.name, "version": text_a.version},
            }
        elif i % 3 == 1:
            model = text_b
            body = {
                "kind": "text",
                "instructions": f"request {i}",
                "settings": {"seed": i, "maxLength": 50 + i},
                "model": {"name": text_b.name, "version": text_b.version},
            }
        else:
            model = image_a
            body = {
                "kind": "image",
                "description": f"request {i}",
                "size": {"width": 64 + i, "height": 96 + i},
                "settings": {"seed": i, "steps": 10 + i},
                "model": {"name": image_a.name, "version": image_a.version},
            }
        response = client.post("/modelmora/v1/requests", json=body)
        assert response.status_code == 202
        requests.append((model, body, response.json()))

    for model, body, accepted in requests:
        status = poll_status(client, accepted["requestId"], wait_seconds=10)
        assert status["state"] == "done", "a request under contention failed rather than waited"
        result = status["result"]

        expected_model = {"name": model.name, "version": model.version}
        assert result["model"] == accepted["model"] == expected_model
        settings_used = result["settingsUsed"]
        assert settings_used["seed"] == body["settings"]["seed"]
        if body["kind"] == "text":
            assert settings_used["maxLength"] == body["settings"]["maxLength"]
        else:
            assert settings_used["steps"] == body["settings"]["steps"]
            assert settings_used["width"] == body["size"]["width"]
            assert settings_used["height"] == body["size"]["height"]
