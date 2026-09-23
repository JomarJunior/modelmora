"""The submit, status and withdraw paths for text requests (Phase 3 MVP).

Generation runs synchronously inside the submit call rather than through a real queue
(Phase 5, T030-T036): stand-in and real models both return fast enough for this to
still satisfy FR-010's "immediate first answer", and every request still passes
through exactly the `waiting -> running -> done/failed` lifecycle FR-014 requires. The
queue phase replaces this loop with real admission, ordering and a background worker
without changing this module's public functions or their return types.
"""

from __future__ import annotations

import base64
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from modelmora.api.validate import model_ref, resolve_text_model
from modelmora.messages import (
    Accepted,
    ModelRef,
    Refusal,
    RequestState,
    RequestStatus,
    Result,
    TextRequest,
)
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.defaults import ModelRegistry
from modelmora.runners.base import Runner
from modelmora.worker.results import text_result


@dataclass
class RequestRecord:
    request_id: uuid.UUID
    caller: str
    submitted_at: datetime
    model: ModelRef
    state: RequestState = "waiting"
    result: Result | None = None
    failure: Refusal | None = None


class RequestStore:
    """Every accepted request, scoped by caller (FR-017)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[uuid.UUID, RequestRecord] = {}

    def add(self, record: RequestRecord) -> None:
        with self._lock:
            self._records[record.request_id] = record

    def get(self, caller: str, request_id: uuid.UUID) -> RequestRecord | None:
        with self._lock:
            record = self._records.get(request_id)
        if record is None or record.caller != caller:
            return None
        return record

    def update(self, request_id: uuid.UUID, **changes: object) -> None:
        with self._lock:
            record = self._records[request_id]
            for key, value in changes.items():
                setattr(record, key, value)

    def withdraw(self, caller: str, request_id: uuid.UUID) -> RequestRecord | None:
        with self._lock:
            record = self._records.get(request_id)
            if record is None or record.caller != caller:
                return None
            if record.state == "waiting":
                record.state = "withdrawn"
        return record


def _ensure_loaded(runner: Runner) -> None:
    if not runner.is_loaded():
        runner.load()


def submit_text_request(
    *,
    store: RequestStore,
    registry: ModelRegistry,
    runners: dict[tuple[str, str], Runner],
    holding_seconds: int,
    caller: str,
    request: TextRequest,
) -> Accepted:
    model = resolve_text_model(registry, request)  # raises ModelMoraRefusal, never queued
    ref = model_ref(model)

    request_id = uuid.uuid4()
    record = RequestRecord(
        request_id=request_id,
        caller=caller,
        submitted_at=datetime.now(UTC),
        model=ref,
        state="waiting",
    )
    store.add(record)

    accepted = Accepted(requestId=request_id, position=0, estimatedWaitSeconds=0, model=ref)

    runner = runners.get((model.name, model.version))
    if runner is None:
        store.update(
            request_id,
            state="failed",
            failure=Refusal(
                reason="model_unavailable", detail=f"{model.name} has no runner attached"
            ),
        )
        return accepted

    store.update(request_id, state="running")
    try:
        _ensure_loaded(runner)
        settings = request.settings
        generated = runner.generate_text(
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
    except ModelMoraRefusal as refusal:
        store.update(request_id, state="failed", failure=refusal.to_message())
        return accepted
    except Exception as exc:  # the model backend failed unexpectedly (spec Edge Cases)
        store.update(
            request_id,
            state="failed",
            failure=Refusal(reason="failed_during_generation", detail=type(exc).__name__),
        )
        return accepted

    result = text_result(model=ref, generated=generated, holding_seconds=holding_seconds)
    store.update(request_id, state="done", result=result)
    return accepted


def request_status(store: RequestStore, caller: str, request_id: uuid.UUID) -> RequestStatus | None:
    record = store.get(caller, request_id)
    if record is None:
        return None
    return RequestStatus(
        requestId=record.request_id,
        state=record.state,
        position=0 if record.state == "waiting" else None,
        estimatedWaitSeconds=0 if record.state == "waiting" else None,
        result=record.result,
        failure=record.failure,
    )


def withdraw_request(
    store: RequestStore, caller: str, request_id: uuid.UUID
) -> RequestStatus | None:
    record = store.withdraw(caller, request_id)
    if record is None:
        return None
    return request_status(store, caller, request_id)
