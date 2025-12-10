from datetime import datetime, timezone
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.types import PastDatetime

from modelmora.shared.custom_types import NaturalNumber
from modelmora.shared.identifiers import StringId


class BaseEntity(BaseModel):
    """Base class for all entities in the system.

    Attributes:
        created_at (datetime): The timestamp when the entity was created (in UTC).
        updated_at (datetime): The timestamp when the entity was last updated (in UTC).
        version (NaturalNumber): The version number of the entity, used for optimistic concurrency control.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
    )

    created_at: PastDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The timestamp when the entity was created (in UTC).",
        frozen=True,  # Pydantic v2 feature to make field immutable
    )

    updated_at: PastDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The timestamp when the entity was last updated (in UTC).",
    )

    version: NaturalNumber = Field(
        default=1,
        description="The version number of the entity, used for optimistic concurrency control.",
        frozen=True,
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "id":
            raise AttributeError("The 'id' attribute is immutable and cannot be modified.")

        if name != "updated_at":
            super().__setattr__("updated_at", datetime.now(timezone.utc))
        super().__setattr__(name, value)
