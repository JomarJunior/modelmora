"""Submitting, checking on and withdrawing requests (T030-T036).

Validation and model resolution (`api/validate.py`) still happen before anything is
queued, exactly as in Phase 3 and 4. What changes here: a validated request becomes a
`QueuedRequest` (`queue/line.py`) and is handed to `state.line`; the single generation
worker (`worker/worker.py`) is the only thing that ever calls `Residency.ensure_loaded`
or a runner's `generate_*`. Two submissions can no longer race for the same model's
residency the way Phase 3's synchronous path could -- the worker serializes every
generation, so that race is closed, not merely narrowed.

`RequestStore` is the caller-visible mirror of what the worker is doing: `mark_running`,
`record_success` and `record_failure` are the callbacks `api/app.py` wires the worker
to, translating a generic `QueuedRequest` outcome into the wire `Result`
(`worker/results.py`) and, for images, into the holding store (`worker/holding.py`).
"""

from __future__ import annotations

import base64
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from modelmora.api.validate import model_ref, resolve_image_runner, resolve_text_model
from modelmora.messages import (
    Accepted,
    ImageRequest,
    ModelKind,
    ModelRef,
    Refusal,
    RequestState,
    RequestStatus,
    Result,
    TextRequest,
)
from modelmora.queue.line import Generate, QueuedRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.runners.base import GeneratedImage, GeneratedText, Runner
from modelmora.worker.results import image_result, text_result

if TYPE_CHECKING:
    from modelmora.api.state import AppState


@dataclass
class RequestRecord:
    request_id: uuid.UUID
    caller: str
    submitted_at: datetime
    model: ModelRef
    state: RequestState = "waiting"
    result: Result | None = None
    failure: Refusal | None = None
    # Set by `mark_running`, for nothing on the wire: T033a measures SC-004 by
    # comparing this against the estimate the caller was given at acceptance.
    started_at: datetime | None = None


class RequestStore:
    """Every accepted request, scoped by caller (FR-017).

    A finished result is held for its caller and then discarded (FR-032). Generated
    content must not outlive its holding time in memory any more than it may reach a
    log (FR-030): every read drops what has expired. `wait_for_change` is the long
    poll (T035): it blocks until a request reaches a terminal state or the caller's
    patience (up to 30 seconds) runs out, whichever comes first.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._records: dict[uuid.UUID, RequestRecord] = {}

    def add(self, record: RequestRecord) -> None:
        with self._condition:
            self._records[record.request_id] = record

    def remove(self, request_id: uuid.UUID) -> None:
        """Un-does `add`: used only when admission itself is refused (FR-015)."""
        with self._condition:
            self._records.pop(request_id, None)

    def _discard_expired_locked(self, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        for record in self._records.values():
            held_until = record.result.heldUntil if record.result else None
            if held_until is not None and held_until <= moment:
                record.result = None

    def get(self, caller: str, request_id: uuid.UUID) -> RequestRecord | None:
        with self._condition:
            self._discard_expired_locked()
            record = self._records.get(request_id)
        if record is None or record.caller != caller:
            return None
        return record

    def update(self, request_id: uuid.UUID, **changes: object) -> None:
        with self._condition:
            record = self._records[request_id]
            for key, value in changes.items():
                setattr(record, key, value)
            self._condition.notify_all()

    def wait_for_change(
        self, caller: str, request_id: uuid.UUID, *, timeout: float
    ) -> RequestRecord | None:
        """Blocks up to `timeout` seconds for a terminal state, or returns sooner.

        The contract's `waitSeconds` asks to "wait this long for the state to change".
        Read literally that could mean "wake me the instant it starts running", but a
        caller polling a request almost always wants to know when it is *done*, not to
        poll again immediately after being woken for a running state it cannot act on.
        This waits for a terminal state (done, failed, withdrawn, stopped before
        completion) or the timeout, whichever comes first.
        """
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                self._discard_expired_locked()
                record = self._records.get(request_id)
                if record is None or record.caller != caller:
                    return None
                if record.state not in ("waiting", "running"):
                    return record
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return record
                self._condition.wait(timeout=remaining)


def _enqueue(
    *,
    state: AppState,
    caller: str,
    kind: ModelKind,
    model: ModelRef,
    runner: Runner,
    generate: Generate,
) -> Accepted:
    assert state.line is not None  # set in AppState.__post_init__
    request_id = uuid.uuid4()
    submitted_at = datetime.now(UTC)
    queued = QueuedRequest(
        request_id=request_id,
        caller=caller,
        kind=kind,
        model=model,
        runner=runner,
        submitted_at=submitted_at,
        generate=generate,
    )

    # The record must exist before the request becomes visible to the worker (the
    # `line.submit` call below), or `mark_running` could run before `add` does.
    state.store.add(
        RequestRecord(request_id=request_id, caller=caller, submitted_at=submitted_at, model=model)
    )
    resident = runner.is_loaded()
    try:
        state.line.submit(queued, estimator=state.estimator, resident=resident)
    except ModelMoraRefusal:
        state.store.remove(request_id)  # never accepted, so never left waiting (FR-015)
        raise

    standing = state.line.standing(request_id)
    position = standing.position if standing is not None else 0
    ahead = standing.ahead_models if standing is not None else []
    estimate = state.estimator.estimate_wait_seconds(
        model=model, resident=resident, ahead_models=ahead
    )
    return Accepted(
        requestId=request_id, position=position, estimatedWaitSeconds=estimate, model=model
    )


def submit_text_request(*, state: AppState, caller: str, request: TextRequest) -> Accepted:
    model = resolve_text_model(state.registry, request)  # raises ModelMoraRefusal, never queued
    ref = model_ref(model)
    runner = state.runners.get((model.name, model.version))
    if runner is None:
        raise ModelMoraRefusal("model_unavailable", detail=f"{model.name} has no runner attached")

    settings = request.settings

    def generate() -> GeneratedText:
        return runner.generate_text(
            instructions=request.instructions,
            conversation=(
                [turn.model_dump() for turn in request.conversation]
                if request.conversation
                else None
            ),
            images=(
                [base64.b64decode(image.base64) for image in request.images]
                if request.images
                else None
            ),
            seed=settings.seed if settings else None,
            max_length=settings.maxLength if settings else None,
            temperature=settings.temperature if settings else None,
        )

    return _enqueue(
        state=state, caller=caller, kind="text", model=ref, runner=runner, generate=generate
    )


def submit_image_request(*, state: AppState, caller: str, request: ImageRequest) -> Accepted:
    # Capability checks (size, footprint versus GPU capacity) raise ModelMoraRefusal
    # here, before anything is queued (T025, US2 acceptance scenario 3).
    model, runner = resolve_image_runner(state.registry, state.runners, state.residency, request)
    ref = model_ref(model)
    settings = request.settings

    def generate() -> GeneratedImage:
        return runner.generate_image(
            description=request.description,
            avoid=request.avoid,
            width=request.size.width,
            height=request.size.height,
            seed=settings.seed if settings else None,
            steps=settings.steps if settings else None,
            guidance=settings.guidance if settings else None,
        )

    return _enqueue(
        state=state, caller=caller, kind="image", model=ref, runner=runner, generate=generate
    )


def mark_running(state: AppState, request: QueuedRequest) -> None:
    state.store.update(request.request_id, state="running", started_at=datetime.now(UTC))


def record_success(
    state: AppState,
    request: QueuedRequest,
    generated: GeneratedText | GeneratedImage,
) -> None:
    if request.kind == "text":
        assert isinstance(generated, GeneratedText)
        result = text_result(
            model=request.model, generated=generated, holding_seconds=state.config.holding_seconds
        )
    else:
        assert isinstance(generated, GeneratedImage)
        result = image_result(
            model=request.model, generated=generated, holding_seconds=state.config.holding_seconds
        )
        assert result.heldUntil is not None  # image_result always sets it
        state.holding.put(request.request_id, generated.png_bytes, held_until=result.heldUntil)
    state.store.update(request.request_id, state="done", result=result)


def record_failure(state: AppState, request: QueuedRequest, error: BaseException) -> None:
    if isinstance(error, ModelMoraRefusal):
        failure = error.to_message()
    else:  # the model backend failed unexpectedly (spec Edge Cases)
        failure = Refusal(reason="failed_during_generation", detail=type(error).__name__)
    state.store.update(request.request_id, state="failed", failure=failure)


def request_status(
    *, state: AppState, caller: str, request_id: uuid.UUID, wait_seconds: float = 0
) -> RequestStatus | None:
    record = (
        state.store.wait_for_change(caller, request_id, timeout=wait_seconds)
        if wait_seconds > 0
        else state.store.get(caller, request_id)
    )
    if record is None:
        return None
    return _status_from_record(state, record)


def _status_from_record(state: AppState, record: RequestRecord) -> RequestStatus:
    position = None
    estimate = None
    if record.state == "waiting" and state.line is not None:
        standing = state.line.standing(record.request_id)
        if standing is not None:
            runner = state.runners.get((record.model.name, record.model.version))
            resident = runner.is_loaded() if runner is not None else False
            position = standing.position
            estimate = state.estimator.estimate_wait_seconds(
                model=record.model, resident=resident, ahead_models=standing.ahead_models
            )
    return RequestStatus(
        requestId=record.request_id,
        state=record.state,
        position=position,
        estimatedWaitSeconds=estimate,
        result=record.result,
        failure=record.failure,
    )


def withdraw_request(
    *, state: AppState, caller: str, request_id: uuid.UUID
) -> RequestStatus | None:
    record = state.store.get(caller, request_id)
    if record is None:
        return None
    if state.line is not None and state.line.withdraw(request_id):
        state.store.update(request_id, state="withdrawn")
    return request_status(state=state, caller=caller, request_id=request_id)
