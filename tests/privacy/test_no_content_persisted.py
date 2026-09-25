"""After a run whose requests carry a unique marker phrase, a search of every log,
error report and the registry finds the marker zero times (T048, FR-030, SC-007).

Activity records may hold the caller, the model, the settings, the times and the
outcome only -- never the instructions, description or generated content itself. No
GPU: stand-in runners actually echo the marker back in their output (`standin.py`
includes the caller's instructions verbatim), which is exactly what makes this a real
check rather than a trivial one -- the marker genuinely passes through ModelMora on its
way to the caller; it must not stick anywhere else.
"""

from __future__ import annotations

import logging

from starlette.testclient import TestClient

from modelmora.api.app import create_app
from tests.conftest import CALLER_TOKEN, build_state

MARKER = "xyzzy-marker-7f19c2-do-not-persist-me"


def _poll(client: TestClient, request_id: str) -> dict:
    response = client.get(f"/modelmora/v1/requests/{request_id}", params={"waitSeconds": 5})
    assert response.status_code == 200
    return response.json()


def test_the_marker_never_reaches_a_log_error_or_the_registry(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    state = build_state()
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})
    try:
        text_submit = client.post(
            "/modelmora/v1/requests",
            json={"kind": "text", "instructions": f"Write a note about {MARKER}, please."},
        )
        text_status = _poll(client, text_submit.json()["requestId"])
        assert MARKER in text_status["result"]["text"]  # the marker really ran through

        image_submit = client.post(
            "/modelmora/v1/requests",
            json={
                "kind": "image",
                "description": f"{MARKER}, a study in light.",
                "size": {"width": 64, "height": 64},
            },
        )
        _poll(client, image_submit.json()["requestId"])

        # A refusal is where the marker would leak into an error report, if it ever
        # did: `detail` must name the problem, never echo the caller's own content
        # (refusals.py).
        refused = client.post(
            "/modelmora/v1/requests",
            json={
                "kind": "text",
                "instructions": MARKER,
                "model": {"name": "no-such-model", "version": "9"},
            },
        )
        assert refused.status_code == 404
        assert MARKER not in refused.text
    finally:
        if state.worker is not None:
            state.worker.stop(timeout=2.0)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert MARKER not in log_text

    # The registry is the one durable store; every text-bearing column it holds, for
    # every model ever added, is the closest a test gets to "every record it keeps"
    # short of reading the SQLite file directly.
    registry_dump = "\n".join(
        " ".join(
            str(field)
            for field in (
                record.name,
                record.version,
                record.source,
                record.license_name,
                record.license_source,
                record.added_by,
                record.license_confirmed_by,
            )
            if field is not None
        )
        for record in state.registry.list_all()
    )
    assert MARKER not in registry_dump
