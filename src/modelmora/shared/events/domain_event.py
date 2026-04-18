from datetime import datetime
from typing import Annotated, Any, ClassVar, Dict

from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler

from modelmora.shared.custom_types import NaturalNumber
from modelmora.shared.identifiers import EventId


class DomainEvent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
    )

    id: Annotated[
        EventId,
        Field(
            default_factory=EventId.generate,
            description="Unique identifier for the domain event",
        ),
    ] = Field(default_factory=EventId.generate)

    event_type: Annotated[
        str,
        Field(
            ...,
            description="Type of the domain event",
        ),
    ]

    aggregate_id: Annotated[
        str,
        Field(
            ...,
            description="Identifier of the aggregate associated with the event",
        ),
    ]

    aggregate_type: Annotated[
        str,
        Field(
            ...,
            description="Type of the aggregate associated with the event",
        ),
    ]

    payload: Annotated[
        Dict[str, Any],
        Field(
            ...,
            description="Payload containing event-specific data",
        ),
    ]

    occurred_at: Annotated[
        datetime,
        Field(
            default_factory=datetime.now,
            description="Timestamp when the event occurred",
        ),
    ] = Field(default_factory=datetime.now)

    version: NaturalNumber
