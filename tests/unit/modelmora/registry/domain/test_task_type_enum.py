import pytest

from modelmora.registry.domain.task_type_enum import TaskTypeEnum


class TestTaskTypeEnum:
    """Test TaskTypeEnum values and behavior."""

    def test_txt2embed_value_should_be_txt2embed(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.TXT2EMBED == "txt2embed"
        assert TaskTypeEnum.TXT2EMBED.value == "txt2embed"

    def test_txt2txt_value_should_be_txt2txt(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.TXT2TXT == "txt2txt"
        assert TaskTypeEnum.TXT2TXT.value == "txt2txt"

    def test_txt2img_value_should_be_txt2img(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.TXT2IMG == "txt2img"
        assert TaskTypeEnum.TXT2IMG.value == "txt2img"

    def test_img2txt_value_should_be_img2txt(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.IMG2TXT == "img2txt"
        assert TaskTypeEnum.IMG2TXT.value == "img2txt"

    def test_img2img_value_should_be_img2img(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.IMG2IMG == "img2img"
        assert TaskTypeEnum.IMG2IMG.value == "img2img"

    def test_audio2txt_value_should_be_audio2txt(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.AUDIO2TXT == "audio2txt"
        assert TaskTypeEnum.AUDIO2TXT.value == "audio2txt"

    def test_txt2audio_value_should_be_txt2audio(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.TXT2AUDIO == "txt2audio"
        assert TaskTypeEnum.TXT2AUDIO.value == "txt2audio"

    def test_classification_value_should_be_classification(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.CLASSIFICATION == "classification"
        assert TaskTypeEnum.CLASSIFICATION.value == "classification"

    def test_object_detection_value_should_be_object_detection(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.OBJECT_DETECTION == "object_detection"
        assert TaskTypeEnum.OBJECT_DETECTION.value == "object_detection"

    def test_question_answering_value_should_be_question_answering(self) -> None:
        # Arrange & Act & Assert
        assert TaskTypeEnum.QUESTION_ANSWERING == "question_answering"
        assert TaskTypeEnum.QUESTION_ANSWERING.value == "question_answering"

    def test_all_enum_members_should_be_accessible(self) -> None:
        # Arrange
        expected_members = {
            "TXT2EMBED",
            "TXT2TXT",
            "TXT2IMG",
            "IMG2TXT",
            "IMG2IMG",
            "AUDIO2TXT",
            "TXT2AUDIO",
            "CLASSIFICATION",
            "OBJECT_DETECTION",
            "QUESTION_ANSWERING",
        }

        # Act
        actual_members = {member.name for member in TaskTypeEnum}

        # Assert
        assert actual_members == expected_members

    def test_enum_should_be_string_type(self) -> None:
        # Arrange & Act & Assert
        assert isinstance(TaskTypeEnum.TXT2EMBED, str)
        assert isinstance(TaskTypeEnum.TXT2TXT, str)
