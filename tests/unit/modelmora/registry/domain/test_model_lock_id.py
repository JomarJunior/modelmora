import pytest

from modelmora.registry.domain.model_lock_id import ModelLockId
from modelmora.shared.identifiers import StringId


class TestModelLockId:
    """Test ModelLockId identifier."""

    def test_create_model_lock_id_should_inherit_from_string_id(self) -> None:
        # Arrange & Act
        lock_id = ModelLockId.generate()

        # Assert
        assert isinstance(lock_id, StringId)
        assert isinstance(lock_id, ModelLockId)

    def test_generate_should_create_unique_ids(self) -> None:
        # Arrange & Act
        id1 = ModelLockId.generate()
        id2 = ModelLockId.generate()

        # Assert
        assert id1 != id2
        assert str(id1) != str(id2)

    def test_model_lock_id_should_be_hashable(self) -> None:
        # Arrange
        lock_id = ModelLockId.generate()

        # Act & Assert
        assert hash(lock_id) is not None

    def test_model_lock_id_can_be_used_in_set(self) -> None:
        # Arrange
        id1 = ModelLockId.generate()
        id2 = ModelLockId.generate()

        # Act
        id_set = {id1, id2, id1}

        # Assert
        assert len(id_set) == 2

    def test_model_lock_id_can_be_used_as_dict_key(self) -> None:
        # Arrange
        lock_id1 = ModelLockId.generate()
        lock_id2 = ModelLockId.generate()

        # Act
        lock_dict = {lock_id1: "Lock 1", lock_id2: "Lock 2"}

        # Assert
        assert lock_dict[lock_id1] == "Lock 1"
        assert lock_dict[lock_id2] == "Lock 2"
