"""Three defects found reviewing the Phase 3 MVP.

Generation is synchronous until the queue lands (Phase 5, T030-T036). That is a stated
shortcut; these tests pin the parts of it that must be true anyway.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from starlette.testclient import TestClient

from modelmora.api.app import create_app
from modelmora.api.requests import RequestRecord, RequestStore
from modelmora.messages import ModelRef, Result
from modelmora.runners.standin import StandInTextRunner
from tests.conftest import CALLER_TOKEN, TEXT_MODEL, build_state

GENERATION_SECONDS = 1.5


def test_a_slow_generation_does_not_stall_other_callers() -> None:
    """A running request must not block the service (FR-010, SC-003).

    Generation is synchronous until the queue lands, so it has to run off the event loop.
    Inline, it holds the loop for its whole duration and every other caller's status and
    availability call waits behind it.

    Driven through ASGI rather than TestClient, which starts a fresh event loop per call
    and so cannot see the loop being blocked at all.
    """
    state = build_state()
    slow = StandInTextRunner(name=TEXT_MODEL.name, version=TEXT_MODEL.version, reads_images=False)
    original = slow.generate_text

    def blocking_generate(**kwargs: object):  # type: ignore[no-untyped-def]
        time.sleep(GENERATION_SECONDS)
        return original(**kwargs)  # type: ignore[arg-type]

    slow.generate_text = blocking_generate  # type: ignore[method-assign]
    state.runners[(TEXT_MODEL.name, TEXT_MODEL.version)] = slow

    async def scenario() -> tuple[int, int, float]:
        transport = httpx.ASGITransport(app=create_app(state))
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://modelmora.test",
            headers={"Authorization": f"Bearer {CALLER_TOKEN}"},
            timeout=30,
        ) as client:
            began = time.monotonic()
            submitting = asyncio.create_task(
                client.post(
                    "/modelmora/v1/requests",
                    json={"kind": "text", "instructions": "a slow one"},
                )
            )
            await asyncio.sleep(0.05)  # let the submission reach the runner
            answer = await client.get("/modelmora/v1/availability")
            elapsed = time.monotonic() - began
            submitted = await submitting
            return submitted.status_code, answer.status_code, elapsed

    submitted_status, availability_status, elapsed = asyncio.run(scenario())

    assert submitted_status == 202
    assert availability_status == 200
    assert elapsed < GENERATION_SECONDS / 2, (
        f"availability took {elapsed:.2f}s while a {GENERATION_SECONDS}s generation ran: "
        "generation is blocking the event loop"
    )


def test_an_image_request_is_refused_with_a_reason_that_is_true() -> None:
    """A refusal a caller cannot act on is worse than none (FR-011).

    Image generation arrives in Phase 4; saying "no image model on record" would be a
    guess about the registry, and wrong as soon as one is added.
    """
    state = build_state()
    client = TestClient(create_app(state), headers={"Authorization": f"Bearer {CALLER_TOKEN}"})

    response = client.post(
        "/modelmora/v1/requests",
        json={"kind": "image", "description": "low tide", "size": {"width": 512, "height": 512}},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["reason"] == "model_unavailable"
    assert "not served yet" in body["detail"]
    assert "on record" not in body["detail"]


def test_a_result_is_discarded_once_its_holding_time_passes() -> None:
    """Generated text is persona output: it must not outlive its hour (FR-030, FR-032)."""
    store = RequestStore()
    request_id = uuid.uuid4()
    model = ModelRef(name=TEXT_MODEL.name, version=TEXT_MODEL.version)
    store.add(
        RequestRecord(
            request_id=request_id,
            caller="sonavida",
            submitted_at=datetime.now(UTC),
            model=model,
            state="done",
            result=Result(
                model=model,
                text="a persona's private words",
                settingsUsed={},
                heldUntil=datetime.now(UTC) - timedelta(seconds=1),
            ),
        )
    )

    record = store.get("sonavida", request_id)

    assert record is not None
    assert record.state == "done"
    assert record.result is None, "an expired result was still being held"


def test_a_result_inside_its_holding_time_is_kept() -> None:
    store = RequestStore()
    request_id = uuid.uuid4()
    model = ModelRef(name=TEXT_MODEL.name, version=TEXT_MODEL.version)
    store.add(
        RequestRecord(
            request_id=request_id,
            caller="sonavida",
            submitted_at=datetime.now(UTC),
            model=model,
            state="done",
            result=Result(
                model=model,
                text="still collectable",
                settingsUsed={},
                heldUntil=datetime.now(UTC) + timedelta(hours=1),
            ),
        )
    )

    record = store.get("sonavida", request_id)

    assert record is not None and record.result is not None
    assert record.result.text == "still collectable"
