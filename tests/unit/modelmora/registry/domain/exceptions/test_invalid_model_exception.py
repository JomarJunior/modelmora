from uuid import UUID

import pytest

from modelmora.registry.domain.exceptions.invalid_model_exception import (
    InvalidModelException,
)
from modelmora.registry.domain.exceptions.registry_exception_codes import (
    RegistryExceptionCodes,
)


class TestInvalidModelException:
    """Test InvalidModelException exception."""

    def test_create_exception_with_model_id_should_succeed(self) -> None:
        # Arrange
        model_id = "invalid/model"

        # Act
        exception = InvalidModelException(model_id=model_id)

        # Assert
        assert exception.model_id == model_id
        assert exception.code == RegistryExceptionCodes.INVALID_MODEL
        assert "The model is invalid." in str(exception)

    def test_create_exception_with_custom_message_should_use_custom_message(
        self,
    ) -> None:
        # Arrange
        model_id = "invalid/model"
        custom_message = "Model validation failed"

        # Act
        exception = InvalidModelException(model_id=model_id, message=custom_message)

        # Assert
        assert exception.message == custom_message

    def test_exception_should_have_trace_id(self) -> None:
        # Arrange
        model_id = "invalid/model"

        # Act
        exception = InvalidModelException(model_id=model_id)

        # Assert
        assert exception.trace_id is not None
        assert isinstance(exception.trace_id, UUID)

    def test_exception_details_should_contain_model_id(self) -> None:
        # Arrange
        model_id = "invalid/model"

        # Act
        exception = InvalidModelException(model_id=model_id)

        # Assert
        assert "model_id" in exception.details
        assert exception.details["model_id"] == model_id

    def test_exception_can_be_raised_and_caught(self) -> None:
        # Arrange
        model_id = "invalid/model"

        # Act & Assert
        with pytest.raises(InvalidModelException) as exc_info:
            raise InvalidModelException(model_id=model_id)

        assert exc_info.value.model_id == model_id
        assert exc_info.value.model_id == model_id
