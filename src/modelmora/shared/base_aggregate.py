from typing import ClassVar, Dict, Generic, TypeVar

from pydantic import ConfigDict, Field

from modelmora.shared.base_entity import BaseEntity
from modelmora.shared.events import EventEmitter

T = TypeVar("T", bound="BaseEntity")


class BaseAggregate(EventEmitter, Generic[T]):  # EventEmitter is a subclass of BaseModel
    """Base class for all aggregate roots in the system.

    Attributes:
        entities (Dict[str, T]): A dictionary mapping entity IDs to their corresponding entities within the
            aggregate.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
    )

    entities: Dict[str, T] = Field(
        default_factory=dict,
        description="A dictionary mapping entity IDs to their corresponding entities within the aggregate.",
    )
