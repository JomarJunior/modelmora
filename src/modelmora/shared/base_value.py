from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class BaseValue(BaseModel):
    """Base class for all value objects in the system."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        use_enum_values=True,
        frozen=True,
        validate_assignment=True,
    )
