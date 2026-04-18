import pytest

from modelmora.registry.domain.model_version_id import ModelVersionId
from modelmora.shared.identifiers import StringId


class TestModelVersionId:
    """Test ModelVersionId identifier."""

    def test_create_model_version_id_should_inherit_from_string_id(self) -> None:
        # Arrange & Act
        version_id = ModelVersionId.generate()

        # Assert
        assert isinstance(version_id, StringId)
        assert isinstance(version_id, ModelVersionId)

    def test_generate_should_create_unique_ids(self) -> None:
        # Arrange & Act
        id1 = ModelVersionId.generate()
        id2 = ModelVersionId.generate()

        # Assert
        assert id1 != id2
        assert str(id1) != str(id2)

    def test_model_version_id_should_be_hashable(self) -> None:
        # Arrange
        version_id = ModelVersionId.generate()

        # Act & Assert
        assert hash(version_id) is not None

    def test_model_version_id_can_be_used_in_set(self) -> None:
        # Arrange
        id1 = ModelVersionId.generate()
        id2 = ModelVersionId.generate()

        # Act
        id_set = {id1, id2, id1}

        # Assert
        assert len(id_set) == 2

    def test_model_version_id_can_be_used_as_dict_key(self) -> None:
        # Arrange
        version_id1 = ModelVersionId.generate()
        version_id2 = ModelVersionId.generate()

        # Act
        version_dict = {version_id1: "Version 1", version_id2: "Version 2"}

        # Assert
        assert version_dict[version_id1] == "Version 1"
        assert version_dict[version_id2] == "Version 2"
