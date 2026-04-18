from uuid import uuid4

from modelmora.registry.domain.exceptions.registry_exception_codes import RegistryExceptionCodes
from modelmora.registry.domain.model_id import ModelId
from modelmora.shared.exceptions import DomainException


class ModelAlreadyExistsException(DomainException):
    """Exception raised when a model already exists."""

    def __init__(self, model_id: ModelId, message: str = "The model already exists.") -> None:
        self.model_id = model_id
        super().__init__(
            RegistryExceptionCodes.MODEL_ALREADY_EXISTS,
            message,
            details={"model_id": model_id},
            trace_id=uuid4(),
        )
