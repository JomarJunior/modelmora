from uuid import uuid4

from modelmora.registry.domain.exceptions.registry_exception_codes import RegistryExceptionCodes
from modelmora.shared.exceptions import DomainException


class InvalidModelException(DomainException):
    """Exception raised when a model is invalid."""

    def __init__(self, model_id: str, message: str = "The model is invalid.") -> None:
        self.model_id = model_id
        super().__init__(
            RegistryExceptionCodes.INVALID_MODEL,
            message,
            details={"model_id": model_id},
            trace_id=uuid4(),
        )
