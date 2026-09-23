"""The loopback ASGI service: all five ModelMora paths.

Binds `127.0.0.1` only (FR-027) and identifies callers by a bearer token that names
them (R-9) -- an ownership marker, not a security boundary; loopback is that boundary.
Test mode (wired by `cli.py`) selects stand-in runners so every path here can be
exercised with no GPU (FR-033, FR-034).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
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
from modelmora.config import BIND_HOST, Config
from modelmora.messages import (
    Availability,
    ImageRequest,
    ModelsList,
    Refusal,
    Servable,
    ServableDefaults,
    ServableModel,
    TextRequest,
)
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.defaults import ModelRegistry
from modelmora.runners.base import Runner


class InvalidBindHost(RuntimeError):
    """Raised when configured with anything other than loopback (FR-027)."""


def assert_loopback_host(host: str) -> None:
    if host != BIND_HOST:
        raise InvalidBindHost(f"ModelMora must bind {BIND_HOST} only, got {host!r} (FR-027)")


@dataclass
class AppState:
    config: Config
    registry: ModelRegistry
    runners: dict[tuple[str, str], Runner] = field(default_factory=dict)
    store: requests_api.RequestStore = field(default_factory=requests_api.RequestStore)


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
            # Off the event loop: generation is synchronous until the queue arrives
            # (Phase 5), and running it inline would stall every other caller's status
            # and availability call for the whole generation, breaking FR-010's
            # immediate first answer for everyone but the submitter.
            accepted = await run_in_threadpool(
                partial(
                    requests_api.submit_text_request,
                    store=state.store,
                    registry=state.registry,
                    runners=state.runners,
                    holding_seconds=state.config.holding_seconds,
                    caller=caller,
                    request=text_request,
                )
            )
        except ModelMoraRefusal as refusal:
            return _refused(
                refusal.http_status, refusal.reason, refusal.detail, refusal.retry_after_seconds
            )
        return JSONResponse(accepted.model_dump(mode="json"), status_code=202)

    if kind == "image":
        try:
            ImageRequest.model_validate(payload)
        except Exception as exc:
            return _refused(400, "invalid_request", detail=type(exc).__name__)
        # Image generation lands in Phase 4 (T022-T026). Say that, rather than blame an
        # empty registry: an image model may well be on record, and a refusal that
        # misstates its reason is one a caller cannot act on (FR-011).
        return _refused(
            404,
            "model_unavailable",
            detail="image generation is not served yet (spec 002 Phase 4)",
        )

    return _refused(400, "invalid_request", detail="kind must be 'text' or 'image'")


async def get_request_status(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    request_id = _parse_request_id(request)
    if request_id is None:
        return _refused(404, "invalid_request", detail="no such request")
    status = requests_api.request_status(state.store, caller, request_id)
    if status is None:
        return _refused(404, "invalid_request", detail="no such request")
    return JSONResponse(status.model_dump(mode="json"))


async def withdraw_request(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    caller: str = request.state.caller
    request_id = _parse_request_id(request)
    if request_id is None:
        return _refused(404, "invalid_request", detail="no such request")
    status = requests_api.withdraw_request(state.store, caller, request_id)
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
    # The holding store for image bytes lands with Phase 4 (T026, worker/holding.py).
    return _refused(404, "model_unavailable", detail="image holding not yet implemented")


async def list_models(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    models = [
        ServableModel(
            name=m.name,
            version=m.version,
            kind=m.kind,
            readsImages=m.reads_images,
            license=m.license,
        )
        for m in state.registry.list_servable()
    ]
    defaults = state.registry.defaults()
    body = ModelsList(
        models=models,
        defaults=ServableDefaults(
            text=defaults["text"].name if defaults["text"] else None,
            textWithImages=(
                defaults["text_with_images"].name if defaults["text_with_images"] else None
            ),
            image=defaults["image"].name if defaults["image"] else None,
        ),
    )
    return JSONResponse(body.model_dump(mode="json"))


async def availability(request: Request) -> Response:
    state: AppState = request.app.state.modelmora
    body = Availability(
        state="running",
        queueLength=0,
        servable=Servable(
            text=len(state.registry.list_servable("text")),
            image=len(state.registry.list_servable("image")),
        ),
    )
    return JSONResponse(body.model_dump(mode="json"))


def create_app(state: AppState) -> Starlette:
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
    )
    app.state.modelmora = state
    return app
