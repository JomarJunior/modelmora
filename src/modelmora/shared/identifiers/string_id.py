from typing import List, TypeVar, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

T = TypeVar("T", bound="StringId")


class StringId(str):
    """A string identifier that must be a valid UUID string.

    This class extends the built-in `str` type and enforces that any instance
    created is a valid UUID string. If the provided string is not a valid UUID,
    a `ValueError` is raised.

    To be inherited for each specific entity's string identifier.
    """

    def __new__(cls, value: Union[str, UUID]) -> "StringId":
        if cls is StringId:
            raise TypeError("StringId cannot be instantiated directly. Please inherit it.")

        try:
            if isinstance(value, UUID):
                value = str(value)
            else:
                UUID(value)
        except ValueError:
            raise ValueError(f"The provided value '{value}' is not a valid UUID string.")
        return str.__new__(cls, value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __str__(self) -> str:
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return super().__eq__(other)

    def __hash__(self) -> int:
        return super().__hash__()

    @classmethod
    def __get_pydantic_core_schema__(cls: type[T], source: type[BaseModel], handler: GetCoreSchemaHandler):
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )

    @classmethod
    def from_strings(cls: type[T], value: List[str]) -> List[T]:
        """Create a list of StringId instances from a list of strings.

        Args:
            value (List[str]): A list of strings to be converted to StringId instances.
        Returns:
            List[StringId]: A list of StringId instances.
        """
        return [cls(v) for v in value]

    @classmethod
    def to_strings(cls, value: List[T]) -> List[str]:
        """Convert a list of StringId instances to a list of strings.

        Args:
            value (List[StringId]): A list of StringId instances to be converted to strings.
        Returns:
            List[str]: A list of strings.
        """
        return [str(v) for v in value]

    @classmethod
    def from_uuids(cls: type[T], value: List[UUID]) -> List[T]:
        """Create a list of StringId instances from a list of UUIDs.

        Args:
            value (List[UUID]): A list of UUIDs to be converted to StringId instances.
        Returns:
            List[StringId]: A list of StringId instances.
        """
        return [cls(v) for v in value]

    @classmethod
    def to_uuids(cls, value: List[T]) -> List[UUID]:
        """Convert a list of StringId instances to a list of UUIDs.

        Args:
            value (List[StringId]): A list of StringId instances to be converted to UUIDs.
        Returns:
            List[UUID]: A list of UUIDs.
        """
        return [UUID(v) for v in value]

    @classmethod
    def generate(cls: type[T]) -> T:
        """Generate a new StringId instance with a random UUID.

        Returns:
            StringId: A new StringId instance.
        """
        return cls(str(uuid4()))
