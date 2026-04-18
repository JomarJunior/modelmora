import pytest

from modelmora.registry.domain.framework_enum import FrameworkEnum


class TestFrameworkEnum:
    """Test FrameworkEnum values and behavior."""

    def test_pytorch_value_should_be_pytorch(self) -> None:
        # Arrange & Act & Assert
        assert FrameworkEnum.PYTORCH == "pytorch"
        assert FrameworkEnum.PYTORCH.value == "pytorch"

    def test_all_enum_members_should_be_accessible(self) -> None:
        # Arrange
        expected_members = {"PYTORCH"}

        # Act
        actual_members = {member.name for member in FrameworkEnum}

        # Assert
        assert actual_members == expected_members

    def test_enum_should_be_string_type(self) -> None:
        # Arrange & Act & Assert
        assert isinstance(FrameworkEnum.PYTORCH, str)
