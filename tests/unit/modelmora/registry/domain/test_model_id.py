import pytest
from pydantic import ValidationError

from modelmora.registry.domain.model_id import ModelId


class TestModelIdInitialization:
    """Test ModelId initialization and validation."""

    def test_create_model_id_with_valid_value_should_succeed(self) -> None:
        # Arrange & Act
        model_id = ModelId(value="openai/gpt-4")

        # Assert
        assert model_id.value == "openai/gpt-4"

    def test_create_model_id_with_hyphen_and_underscore_should_succeed(self) -> None:
        # Arrange & Act
        model_id = ModelId(value="my-org_123/my-model_v2")

        # Assert
        assert model_id.value == "my-org_123/my-model_v2"

    def test_create_model_id_without_slash_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value="invalidmodelid")

    def test_create_model_id_with_multiple_slashes_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value="org/repo/extra")

    def test_create_model_id_with_empty_org_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value="/repo")

    def test_create_model_id_with_empty_repo_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value="org/")

    def test_create_model_id_with_special_characters_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value="org@invalid/repo#test")

    def test_create_model_id_exceeding_max_length_should_raise_error(self) -> None:
        # Arrange
        long_value = "a" * 150 + "/" + "b" * 150  # Over 200 characters

        # Act & Assert
        with pytest.raises(ValidationError):
            ModelId(value=long_value)


class TestModelIdProperties:
    """Test ModelId property accessors."""

    def test_org_property_should_return_organization_part(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act
        org = model_id.org

        # Assert
        assert org == "openai"

    def test_repo_property_should_return_repository_part(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act
        repo = model_id.repo

        # Assert
        assert repo == "gpt-4"

    def test_org_and_repo_with_complex_names_should_work(self) -> None:
        # Arrange
        model_id = ModelId(value="meta-ai_v2/llama-3_70B")

        # Act & Assert
        assert model_id.org == "meta-ai_v2"
        assert model_id.repo == "llama-3_70B"


class TestModelIdStringRepresentations:
    """Test ModelId string representations."""

    def test_str_representation_should_return_value(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act
        result = str(model_id)

        # Assert
        assert result == "openai/gpt-4"

    def test_repr_representation_should_return_detailed_string(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act
        result = repr(model_id)

        # Assert
        assert result == "ModelId(value=openai/gpt-4)"


class TestModelIdEquality:
    """Test ModelId equality and hashing."""

    def test_equal_model_ids_with_same_value_should_be_equal(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="openai/gpt-4")

        # Act & Assert
        assert model_id1 == model_id2

    def test_different_model_ids_should_not_be_equal(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="anthropic/claude")

        # Act & Assert
        assert model_id1 != model_id2

    def test_model_id_equality_with_non_model_id_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act
        result = model_id.__eq__("not a model id")

        # Assert
        assert result == NotImplemented

    def test_equal_model_ids_should_have_equal_hashes(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="openai/gpt-4")

        # Act & Assert
        assert hash(model_id1) == hash(model_id2)

    def test_different_model_ids_should_have_different_hashes(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="anthropic/claude")

        # Act & Assert
        assert hash(model_id1) != hash(model_id2)

    def test_model_id_can_be_used_in_set(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="openai/gpt-4")
        model_id3 = ModelId(value="anthropic/claude")

        # Act
        model_set = {model_id1, model_id2, model_id3}

        # Assert
        assert len(model_set) == 2

    def test_model_id_can_be_used_as_dict_key(self) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="openai/gpt-4")
        model_id3 = ModelId(value="anthropic/claude")

        # Act
        model_dict = {model_id1: "first", model_id2: "second", model_id3: "third"}

        # Assert
        assert len(model_dict) == 2
        assert model_dict[model_id1] == "second"
        assert model_dict[model_id3] == "third"


class TestModelIdImmutability:
    """Test ModelId immutability (frozen=True)."""

    def test_modify_model_id_value_should_raise_error(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")

        # Act & Assert
        with pytest.raises(ValidationError):
            model_id.value = "new/value"
