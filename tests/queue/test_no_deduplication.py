"""T029a: two callers asking for exactly the same thing get two requests and two
results (spec Edge Cases).

This is deliberately the opposite of the Studio Link's send-mark rule: **🧠 ModelMora**
never decides that two requests are the same, no matter how identical their content.
"""

from __future__ import annotations

from tests.queue.conftest import (
    CALLER_TOKEN,
    OTHER_TOKEN,
    add_text_model,
    build_queue_state,
    poll_status,
)

IDENTICAL_BODY = {
    "kind": "text",
    "instructions": "Write a short artist statement.",
    "settings": {"seed": 7, "maxLength": 100},
}


def test_two_callers_submitting_the_same_request_get_two_results(make_client) -> None:
    state = build_queue_state(line_limit=10)
    add_text_model(state, "synthetic-text-dedup")
    sonavida = make_client(state, token=CALLER_TOKEN)
    curagusta = make_client(state, token=OTHER_TOKEN)

    first = sonavida.post("/modelmora/v1/requests", json=IDENTICAL_BODY)
    second = curagusta.post("/modelmora/v1/requests", json=IDENTICAL_BODY)

    assert first.status_code == 202 and second.status_code == 202
    assert first.json()["requestId"] != second.json()["requestId"], (
        "two distinct requests were merged into one"
    )

    first_status = poll_status(sonavida, first.json()["requestId"])
    second_status = poll_status(curagusta, second.json()["requestId"])

    assert first_status["state"] == "done" and second_status["state"] == "done"
    # Each caller gets its own result: neither can see the other's by asking for its
    # own id under a different token, and both actually ran (not one skipped).
    assert sonavida.get(f"/modelmora/v1/requests/{second.json()['requestId']}").status_code == 404
    assert curagusta.get(f"/modelmora/v1/requests/{first.json()['requestId']}").status_code == 404
