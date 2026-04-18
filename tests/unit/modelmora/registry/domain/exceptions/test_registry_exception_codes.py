import pytest

from modelmora.registry.domain.exceptions.registry_exception_codes import (
    RegistryExceptionCodes,
)


class TestRegistryExceptionCodes:
    """Test RegistryExceptionCodes enum values."""

    def test_invalid_model_code_should_be_invalid_model(self) -> None:
        # Arrange & Act & Assert
        assert RegistryExceptionCodes.INVALID_MODEL == "invalid_model"
        assert RegistryExceptionCodes.INVALID_MODEL.value == "invalid_model"

    def test_model_already_exists_code_should_be_model_already_exists(self) -> None:
        # Arrange & Act & Assert
        assert RegistryExceptionCodes.MODEL_ALREADY_EXISTS == "model_already_exists"
        assert RegistryExceptionCodes.MODEL_ALREADY_EXISTS.value == "model_already_exists"

    def test_model_not_found_code_should_be_model_not_found(self) -> None:
        # Arrange & Act & Assert
        assert RegistryExceptionCodes.MODEL_NOT_FOUND == "model_not_found"
        assert RegistryExceptionCodes.MODEL_NOT_FOUND.value == "model_not_found"

    def test_all_enum_members_should_be_accessible(self) -> None:
        # Arrange
        expected_members = {
            "INVALID_MODEL",
            "MODEL_ALREADY_EXISTS",
            "MODEL_NOT_FOUND",
        }

        # Act
        actual_members = {member.name for member in RegistryExceptionCodes}

        # Assert
        assert actual_members == expected_members

    def test_enum_should_be_string_type(self) -> None:
        # Arrange & Act & Assert
        assert isinstance(RegistryExceptionCodes.INVALID_MODEL, str)
        assert isinstance(RegistryExceptionCodes.MODEL_ALREADY_EXISTS, str)
        assert isinstance(RegistryExceptionCodes.MODEL_NOT_FOUND, str)
