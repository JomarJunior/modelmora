import pytest
from pydantic import ValidationError

from modelmora.registry.domain.task_type import TaskType
from modelmora.registry.domain.task_type_enum import TaskTypeEnum


class TestTaskTypeInitialization:
    """Test TaskType initialization and validation."""

    def test_create_task_type_with_valid_enum_should_succeed(self) -> None:
        # Arrange & Act
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Assert
        assert task_type.value == TaskTypeEnum.TXT2EMBED

    def test_create_task_type_with_all_valid_enums_should_succeed(self) -> None:
        # Arrange
        all_task_types = [
            TaskTypeEnum.TXT2EMBED,
            TaskTypeEnum.TXT2TXT,
            TaskTypeEnum.TXT2IMG,
            TaskTypeEnum.IMG2TXT,
            TaskTypeEnum.IMG2IMG,
            TaskTypeEnum.AUDIO2TXT,
            TaskTypeEnum.TXT2AUDIO,
            TaskTypeEnum.CLASSIFICATION,
            TaskTypeEnum.OBJECT_DETECTION,
            TaskTypeEnum.QUESTION_ANSWERING,
        ]

        # Act & Assert
        for task_type_enum in all_task_types:
            task_type = TaskType(value=task_type_enum)
            assert task_type.value == task_type_enum

    def test_create_task_type_with_invalid_value_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            TaskType(value="invalid_task_type")

    def test_create_task_type_without_value_should_raise_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            TaskType()


class TestTaskTypeSerialization:
    """Test TaskType serialization methods."""

    def test_serialize_task_type_should_return_string(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act
        serialized = task_type.serialize()

        # Assert
        assert isinstance(serialized, str)
        assert serialized == "txt2embed"

    def test_str_representation_should_return_enum_value(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act
        result = str(task_type)

        # Assert
        assert result == "txt2txt"

    def test_repr_representation_should_return_detailed_string(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.IMG2TXT)

        # Act
        result = repr(task_type)

        # Assert
        assert result == "TaskType(value=img2txt)"


class TestTaskTypeEquality:
    """Test TaskType equality and hashing."""

    def test_equal_task_types_with_same_value_should_be_equal(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type2 = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act & Assert
        assert task_type1 == task_type2

    def test_different_task_types_should_not_be_equal(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type2 = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act & Assert
        assert task_type1 != task_type2

    def test_task_type_equality_with_non_task_type_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act
        result = task_type.__eq__("not a task type")

        # Assert
        assert result == NotImplemented

    def test_equal_task_types_should_have_equal_hashes(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2IMG)
        task_type2 = TaskType(value=TaskTypeEnum.TXT2IMG)

        # Act & Assert
        assert hash(task_type1) == hash(task_type2)

    def test_different_task_types_should_have_different_hashes(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2IMG)
        task_type2 = TaskType(value=TaskTypeEnum.IMG2TXT)

        # Act & Assert
        assert hash(task_type1) != hash(task_type2)

    def test_task_type_can_be_used_in_set(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type2 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type3 = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act
        task_set = {task_type1, task_type2, task_type3}

        # Assert
        assert len(task_set) == 2

    def test_task_type_can_be_used_as_dict_key(self) -> None:
        # Arrange
        task_type1 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type2 = TaskType(value=TaskTypeEnum.TXT2EMBED)
        task_type3 = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act
        task_dict = {task_type1: "first", task_type2: "second", task_type3: "third"}

        # Assert
        assert len(task_dict) == 2
        assert task_dict[task_type1] == "second"
        assert task_dict[task_type3] == "third"


class TestTaskTypeInputSchema:
    """Test TaskType input schema generation."""

    def test_get_input_schema_for_txt2embed_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert schema["properties"]["text"]["type"] == "string"
        assert schema["required"] == ["text"]

    def test_get_input_schema_for_txt2txt_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "max_tokens" in schema["properties"]
        assert schema["properties"]["prompt"]["type"] == "string"
        assert schema["properties"]["max_tokens"]["type"] == "integer"
        assert schema["properties"]["max_tokens"]["default"] == 100
        assert schema["required"] == ["prompt"]

    def test_get_input_schema_for_txt2img_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2IMG)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "width" in schema["properties"]
        assert "height" in schema["properties"]
        assert schema["properties"]["width"]["default"] == 512
        assert schema["properties"]["height"]["default"] == 512
        assert schema["required"] == ["prompt", "negative_prompt"]

    def test_get_input_schema_for_img2txt_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.IMG2TXT)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert schema["properties"]["image"]["type"] == "string"
        assert schema["required"] == ["image"]

    def test_get_input_schema_for_img2img_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.IMG2IMG)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "strength" in schema["properties"]
        assert schema["properties"]["strength"]["default"] == 0.8
        assert schema["required"] == ["image", "prompt", "negative_prompt"]

    def test_get_input_schema_for_audio2txt_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.AUDIO2TXT)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "audio" in schema["properties"]
        assert "language" in schema["properties"]
        assert schema["properties"]["audio"]["type"] == "string"
        assert schema["required"] == ["audio"]

    def test_get_input_schema_for_txt2audio_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2AUDIO)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "voice" in schema["properties"]
        assert "speed" in schema["properties"]
        assert schema["properties"]["speed"]["default"] == 1.0
        assert schema["required"] == ["text"]

    def test_get_input_schema_for_classification_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.CLASSIFICATION)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "input" in schema["properties"]
        assert "labels" in schema["properties"]
        assert schema["properties"]["input"]["type"] == "string"
        assert schema["properties"]["labels"]["type"] == "array"
        assert schema["properties"]["labels"]["items"]["type"] == "string"
        assert schema["required"] == ["input"]

    def test_get_input_schema_for_object_detection_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.OBJECT_DETECTION)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "confidence_threshold" in schema["properties"]
        assert schema["properties"]["confidence_threshold"]["default"] == 0.5
        assert schema["required"] == ["image"]

    def test_get_input_schema_for_question_answering_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.QUESTION_ANSWERING)

        # Act
        schema = task_type.get_input_schema()

        # Assert
        assert schema["type"] == "object"
        assert "question" in schema["properties"]
        assert "context" in schema["properties"]
        assert schema["properties"]["question"]["type"] == "string"
        assert schema["properties"]["context"]["type"] == "string"
        assert schema["required"] == ["question", "context"]


class TestTaskTypeOutputSchema:
    """Test TaskType output schema generation."""

    def test_get_output_schema_for_txt2embed_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "embedding" in schema["properties"]
        assert schema["properties"]["embedding"]["type"] == "array"
        assert schema["properties"]["embedding"]["items"]["type"] == "number"

    def test_get_output_schema_for_txt2txt_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2TXT)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert schema["properties"]["text"]["type"] == "string"

    def test_get_output_schema_for_txt2img_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2IMG)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "image_uri" in schema["properties"]
        assert schema["properties"]["image_uri"]["type"] == "string"

    def test_get_output_schema_for_img2txt_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.IMG2TXT)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert schema["properties"]["text"]["type"] == "string"

    def test_get_output_schema_for_img2img_should_return_correct_schema(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.IMG2IMG)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "image_uri" in schema["properties"]
        assert schema["properties"]["image_uri"]["type"] == "string"

    def test_get_output_schema_for_audio2txt_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.AUDIO2TXT)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "language" in schema["properties"]
        assert schema["properties"]["text"]["type"] == "string"
        assert schema["properties"]["language"]["type"] == "string"

    def test_get_output_schema_for_txt2audio_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2AUDIO)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "audio_uri" in schema["properties"]
        assert schema["properties"]["audio_uri"]["type"] == "string"

    def test_get_output_schema_for_classification_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.CLASSIFICATION)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "label" in schema["properties"]
        assert "score" in schema["properties"]
        assert "scores" in schema["properties"]
        assert schema["properties"]["label"]["type"] == "string"
        assert schema["properties"]["score"]["type"] == "number"
        assert schema["properties"]["scores"]["type"] == "array"
        assert schema["properties"]["scores"]["items"]["type"] == "object"
        assert "label" in schema["properties"]["scores"]["items"]["properties"]
        assert "score" in schema["properties"]["scores"]["items"]["properties"]

    def test_get_output_schema_for_object_detection_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.OBJECT_DETECTION)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "detections" in schema["properties"]
        assert schema["properties"]["detections"]["type"] == "array"
        detection_item = schema["properties"]["detections"]["items"]
        assert detection_item["type"] == "object"
        assert "label" in detection_item["properties"]
        assert "score" in detection_item["properties"]
        assert "bbox" in detection_item["properties"]
        assert detection_item["properties"]["bbox"]["type"] == "object"
        bbox_props = detection_item["properties"]["bbox"]["properties"]
        assert "x" in bbox_props
        assert "y" in bbox_props
        assert "width" in bbox_props
        assert "height" in bbox_props

    def test_get_output_schema_for_question_answering_should_return_correct_schema(
        self,
    ) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.QUESTION_ANSWERING)

        # Act
        schema = task_type.get_output_schema()

        # Assert
        assert schema["type"] == "object"
        assert "answer" in schema["properties"]
        assert "score" in schema["properties"]
        assert "start" in schema["properties"]
        assert "end" in schema["properties"]
        assert schema["properties"]["answer"]["type"] == "string"
        assert schema["properties"]["score"]["type"] == "number"
        assert schema["properties"]["start"]["type"] == "integer"
        assert schema["properties"]["end"]["type"] == "integer"


class TestTaskTypeImmutability:
    """Test TaskType immutability (frozen=True)."""

    def test_modify_task_type_value_should_raise_error(self) -> None:
        # Arrange
        task_type = TaskType(value=TaskTypeEnum.TXT2EMBED)

        # Act & Assert
        with pytest.raises(ValidationError):
            task_type.value = TaskTypeEnum.TXT2TXT
