from uuid import uuid4

from modelmora.registry.domain.exceptions.registry_exception_codes import RegistryExceptionCodes
from modelmora.registry.domain.model_id import ModelId
from modelmora.shared.exceptions import DomainException


class ModelNotFoundException(DomainException):
    """Exception raised when a model is not found."""

    def __init__(self, model_id: ModelId, message: str = "The model was not found.") -> None:
        self.model_id = model_id
        super().__init__(
            RegistryExceptionCodes.MODEL_NOT_FOUND,
            message,
            details={"model_id": model_id},
            trace_id=uuid4(),
        )
