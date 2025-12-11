import pytest

from modelmora.registry.domain.model_catalog_id import ModelCatalogId
from modelmora.shared.identifiers import StringId


class TestModelCatalogId:
    """Test ModelCatalogId identifier."""

    def test_create_model_catalog_id_should_inherit_from_string_id(self) -> None:
        # Arrange & Act
        catalog_id = ModelCatalogId.generate()

        # Assert
        assert isinstance(catalog_id, StringId)
        assert isinstance(catalog_id, ModelCatalogId)

    def test_generate_should_create_unique_ids(self) -> None:
        # Arrange & Act
        id1 = ModelCatalogId.generate()
        id2 = ModelCatalogId.generate()

        # Assert
        assert id1 != id2
        assert str(id1) != str(id2)

    def test_model_catalog_id_should_be_hashable(self) -> None:
        # Arrange
        catalog_id = ModelCatalogId.generate()

        # Act & Assert
        assert hash(catalog_id) is not None

    def test_model_catalog_id_can_be_used_in_set(self) -> None:
        # Arrange
        id1 = ModelCatalogId.generate()
        id2 = ModelCatalogId.generate()

        # Act
        id_set = {id1, id2, id1}

        # Assert
        assert len(id_set) == 2

    def test_model_catalog_id_can_be_used_as_dict_key(self) -> None:
        # Arrange
        catalog_id1 = ModelCatalogId.generate()
        catalog_id2 = ModelCatalogId.generate()

        # Act
        catalog_dict = {catalog_id1: "Catalog 1", catalog_id2: "Catalog 2"}

        # Assert
        assert catalog_dict[catalog_id1] == "Catalog 1"
        assert catalog_dict[catalog_id2] == "Catalog 2"
