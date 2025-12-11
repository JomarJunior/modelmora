from typing import Annotated

from pydantic import Field, field_validator

from modelmora.shared import BaseValue


class ModelId(BaseValue):
    """Represents the unique identifier for a model in the format {org}/{repo}.

    Attributes:
        value (str): The unique identifier for the model, formatted as {org}/{repo}.

    Examples:
        >>> ModelId(value="openai/gpt-4")
        ModelId(value='openai/gpt-4')
    """

    value: Annotated[
        str,
        Field(
            pattern=r"^[a-zA-Z0-9-_]+\/[a-zA-Z0-9-_]+$",
            max_length=200,
            description="Reference to parent model entity. Format: {org}/{repo}",
        ),
    ]

    @property
    def org(self) -> str:
        """Returns the organization part of the ModelId."""
        return self.value.split("/", 1)[0]

    @property
    def repo(self) -> str:
        """Returns the repository part of the ModelId."""
        return self.value.split("/", 1)[1]

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ModelId(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelId):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
