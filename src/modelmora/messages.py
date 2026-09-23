"""Pydantic v2 models for every ModelMora message.

Checked against the hub's `modelmora-v1.yaml` by `tests/api/test_contract_drift.py`.
Every schema in the contract is closed (`additionalProperties: false`): an unknown
field is a refusal, not an ignored extra.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ModelKind = Literal["text", "image"]

RequestState = Literal[
    "waiting",
    "running",
    "done",
    "failed",
    "withdrawn",
    "stopped_before_completion",
]

RefusalReason = Literal[
    "busy",
    "starting",
    "stopping",
    "unknown_model",
    "model_unavailable",
    "invalid_request",
    "cannot_be_served_on_this_studio",
    "failed_during_generation",
]

# Filter disclosure is registry metadata (T038), not part of the wire contract, but the
# closed reason set is defined here since refusals.py depends on it too.
FilterDisclosure = Literal["none", "disclosed", "undisclosable"]


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRef(ClosedModel):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)


class ConversationTurn(ClosedModel):
    speaker: Literal["caller", "model"]
    text: str = Field(max_length=200000)


class ImageInput(ClosedModel):
    mediaType: Literal["image/png", "image/jpeg", "image/webp"]
    base64: str


class TextSettings(ClosedModel):
    seed: int | None = None
    maxLength: int | None = Field(default=None, ge=1, le=32000)
    temperature: float | None = Field(default=None, ge=0, le=2)


class TextRequest(ClosedModel):
    kind: Literal["text"]
    model: ModelRef | None = None
    instructions: str = Field(min_length=1, max_length=200000)
    conversation: list[ConversationTurn] | None = Field(default=None, max_length=200)
    images: list[ImageInput] | None = Field(default=None, max_length=8)
    settings: TextSettings | None = None


class Size(ClosedModel):
    width: int = Field(ge=64, le=4096)
    height: int = Field(ge=64, le=4096)


class ImageSettings(ClosedModel):
    seed: int | None = None
    steps: int | None = Field(default=None, ge=1, le=200)
    guidance: float | None = Field(default=None, ge=0, le=30)


class ImageRequest(ClosedModel):
    kind: Literal["image"]
    model: ModelRef | None = None
    description: str = Field(min_length=1, max_length=20000)
    avoid: str | None = Field(default=None, max_length=20000)
    size: Size
    settings: ImageSettings | None = None


class Accepted(ClosedModel):
    requestId: uuid.UUID
    position: int = Field(ge=0)
    estimatedWaitSeconds: int = Field(ge=0)
    model: ModelRef


class Refusal(ClosedModel):
    reason: RefusalReason
    detail: str | None = Field(default=None, max_length=2000)
    retryAfterSeconds: int | None = Field(default=None, ge=0)


class Result(ClosedModel):
    model: ModelRef
    text: str | None = None
    imageAvailable: bool = False
    settingsUsed: dict[str, Any]
    filterNote: str | None = None
    heldUntil: datetime | None = None


class RequestStatus(ClosedModel):
    requestId: uuid.UUID
    state: RequestState
    position: int | None = Field(default=None, ge=0)
    estimatedWaitSeconds: int | None = Field(default=None, ge=0)
    result: Result | None = None
    failure: Refusal | None = None


class ServableModel(ClosedModel):
    name: str
    version: str
    kind: ModelKind
    readsImages: bool
    license: str


class ServableDefaults(ClosedModel):
    text: str | None
    textWithImages: str | None
    image: str | None


class ModelsList(ClosedModel):
    models: list[ServableModel]
    defaults: ServableDefaults


class Servable(ClosedModel):
    text: int = Field(ge=0)
    image: int = Field(ge=0)


class Availability(ClosedModel):
    state: Literal["starting", "running", "stopping"]
    queueLength: int = Field(ge=0)
    servable: Servable
