"""The loopback ASGI service: all five ModelMora paths.

Binds `127.0.0.1` only (FR-027) and identifies callers by a bearer token that names
them (R-9) -- an ownership marker, not a security boundary; loopback is that boundary.
Test mode (wired by `cli.py`) selects stand-in runners so every path here can be
exercised with no GPU (FR-033, FR-034).

`create_app` is also where the single generation worker (T032) is built and started:
submitting a request only validates and enqueues it (`api/requests.py`), so nothing on
the request path ever calls a runner's `generate_*` -- that happens on the worker's own
thread, which is what keeps every answer here immediate (SC-003) regardless of how long
generation takes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from modelmora.api import requests as requests_api
from modelmora.api.models import build_models_list
from modelmora.api.state import AppState
from modelmora.config import BIND_HOST, Config
from modelmora.messages import (
    Availability,
    ImageRequest,
    Refusal,
    Servable,
    TextRequest,
)
from modelmora.queue.line import QueuedRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.runners.base import GeneratedImage, GeneratedText
from modelmora.worker.worker import Worker

__all__ = ["AppState", "InvalidBindHost", "assert_loopback_host", "create_app"]


class InvalidBindHost(RuntimeError):
    """Raised when configured with anything other than loopback (FR-027)."""


def assert_loopback_host(host: str) -> None:
    if host != BIND_HOST:
        raise InvalidBindHost(f"ModelMora must bind {BIND_HOST} only, got {host!r} (FR-027)")


def _refused(
    status_code: int,
    reason: str,
    detail: str | None = None,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    body = Refusal(reason=reason, detail=detail, retryAfterSeconds=retry_after_seconds)  # type: ignore[arg-type]
    return JSONResponse(body.model_dump(mode="json"), status_code=status_code)


def _caller_from_request(request: Request, config: Config) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[len("bearer ") :].strip()
    return config.caller_for_token(token)


class RequireCallerTokenMiddleware(BaseHTTPMiddleware):
    """Every path names its caller (R-9); there is no anonymous access."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        state: AppState = request.app.state.modelmora
        caller = _caller_from_request(request, state.config)
        if caller is None:
            return _refused(401, "invalid_request", detail="missing or unknown caller token")
        request.state.caller = caller
        return await call_next(request)


def _parse_request_id(request: Request) -> uuid.UUID | None:
    try:
        return uuid.UUID(request.path_params["requestId"])
    except (ValueError, KeyError):
        return None


def _parse_wait_seconds(request: Request) -> int | None:
    """0-30 (the contract's `waitSeconds`); `None` means the value itself is invalid."""
    raw = request.query_params.get("waitSeconds")
    if raw is None:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if 0 <= value <= 30 else None


async def submit_request(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    try:
        payload: Any = await request.json()
    except ValueError:
        return _refused(400, "invalid_request", detail="malformed JSON body")

    kind = payload.get("kind") if isinstance(payload, dict) else None

    if kind == "text":
        try:
            text_request = TextRequest.model_validate(payload)
        except Exception as exc:  # pydantic ValidationError, kept out of caller content
            return _refused(400, "invalid_request", detail=type(exc).__name__)
        try:
            # Validating and enqueueing is fast: no generation happens on this path
            # (R-6), so there is nothing here that needs to run off the event loop.
            accepted = requests_api.submit_text_request(
                state=state, caller=caller, request=text_request
            )
        except ModelMoraRefusal as refusal:
            return _refused(
                refusal.http_status, refusal.reason, refusal.detail, refusal.retry_after_seconds
            )
        return JSONResponse(accepted.model_dump(mode="json"), status_code=202)

    if kind == "image":
        try:
            image_request = ImageRequest.model_validate(payload)
        except Exception as exc:
            return _refused(400, "invalid_request", detail=type(exc).__name__)
        try:
            accepted = requests_api.submit_image_request(
                state=state, caller=caller, request=image_request
            )
        except ModelMoraRefusal as refusal:
            return _refused(
                refusal.http_status, refusal.reason, refusal.detail, refusal.retry_after_seconds
            )
        return JSONResponse(accepted.model_dump(mode="json"), status_code=202)

    return _refused(400, "invalid_request", detail="kind must be 'text' or 'image'")


async def get_request_status(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    request_id = _parse_request_id(request)
    if request_id is None:
        return _refused(404, "invalid_request", detail="no such request")
    wait_seconds = _parse_wait_seconds(request)
    if wait_seconds is None:
        return _refused(400, "invalid_request", detail="waitSeconds must be 0-30")
    # The long poll (up to 30s, T035) blocks a real thread, so it must run off the
    # event loop or it would stall every other caller's request meanwhile (SC-003).
    status = await run_in_threadpool(
        partial(
            requests_api.request_status,
            state=state,
            caller=caller,
            request_id=request_id,
            wait_seconds=wait_seconds,
        )
    )
    if status is None:
        return _refused(404, "invalid_request", detail="no such request")
    return JSONResponse(status.model_dump(mode="json"))


async def withdraw_request(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    request_id = _parse_request_id(request)
    if request_id is None:
        return _refused(404, "invalid_request", detail="no such request")
    status = requests_api.withdraw_request(state=state, caller=caller, request_id=request_id)
    if status is None:
        return _refused(404, "invalid_request", detail="no such request")
    return JSONResponse(status.model_dump(mode="json"))


async def fetch_result_image(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    request_id = _parse_request_id(request)
    if request_id is None:
        return _refused(404, "invalid_request", detail="no such request")
    record = state.store.get(caller, request_id)
    if record is None or record.result is None or not record.result.imageAvailable:
        return _refused(404, "invalid_request", detail="no such image")
    png_bytes = state.holding.get(request_id)  # None once past heldUntil (FR-032)
    if png_bytes is None:
        return _refused(404, "invalid_request", detail="image no longer held")
    return Response(png_bytes, media_type="image/png")


async def list_models(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    body = build_models_list(state)
    return JSONResponse(body.model_dump(mode="json"))


async def availability(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    # `state` (starting/stopping) and draining the line on shutdown are T046's job
    # (Phase 7); the line's length is real as of T030, and every caller sees the same
    # number, never anything about who else is in it (FR-017).
    queue_length = len(state.line) if state.line is not None else 0
    body = Availability(
        state="running",
        queueLength=queue_length,
        servable=Servable(
            text=len(state.registry.list_servable("text")),
            image=len(state.registry.list_servable("image")),
        ),
    )
    return JSONResponse(body.model_dump(mode="json"))


def _build_worker(state: AppState) -> Worker:
    assert state.line is not None  # set in AppState.__post_init__

    def on_running(request: QueuedRequest) -> None:
        requests_api.mark_running(state, request)

    def on_done(
        request: QueuedRequest, generated: GeneratedText | GeneratedImage, elapsed: float
    ) -> None:
        del elapsed  # the worker has already recorded it for the estimator (T033)
        requests_api.record_success(state, request, generated)

    def on_failed(request: QueuedRequest, error: BaseException) -> None:
        requests_api.record_failure(state, request, error)

    return Worker(
        line=state.line,
        residency_provider=lambda: state.residency,
        estimator=state.estimator,
        overtaking_seconds=state.config.overtaking_seconds,
        idle_unload_seconds=state.config.idle_unload_seconds,
        on_running=on_running,
        on_done=on_done,
        on_failed=on_failed,
    )


def _lifespan(state: AppState) -> Any:
    """Nothing outlives the process: the worker stops, then held images are wiped
    (T026, R-7). Graceful draining of open requests into `stopped_before_completion`
    is T046's job (Phase 7); this only stops the thread cleanly."""

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if state.worker is not None:
                state.worker.stop()
            state.holding.wipe()

    return lifespan


def create_app(state: AppState) -> Starlette:
    if state.worker is None:
        state.worker = _build_worker(state)
        state.worker.start()

    app = Starlette(
        routes=[
            Route("/modelmora/v1/requests", submit_request, methods=["POST"]),
            Route("/modelmora/v1/requests/{requestId}", get_request_status, methods=["GET"]),
            Route("/modelmora/v1/requests/{requestId}", withdraw_request, methods=["DELETE"]),
            Route(
                "/modelmora/v1/requests/{requestId}/image",
                fetch_result_image,
                methods=["GET"],
            ),
            Route("/modelmora/v1/models", list_models, methods=["GET"]),
            Route("/modelmora/v1/availability", availability, methods=["GET"]),
        ],
        middleware=[Middleware(RequireCallerTokenMiddleware)],
        lifespan=_lifespan(state),
    )
    app.state.modelmora = state
    return app
