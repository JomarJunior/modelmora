from typing import Annotated

from pydantic import Field, model_serializer

from modelmora.registry.domain.schema import Schema
from modelmora.registry.domain.task_type_enum import TaskTypeEnum
from modelmora.shared import BaseValue


class TaskType(BaseValue):
    """Represents the type of task a model is designed to perform."""

    value: Annotated[
        TaskTypeEnum,
        Field(
            description="The type of task the model is designed to perform.",
        ),
    ]

    @model_serializer
    def serialize(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"TaskType(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskType):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def get_input_schema(self) -> Schema:
        schemas = {
            TaskTypeEnum.TXT2EMBED: {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
            TaskTypeEnum.TXT2TXT: {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "max_tokens": {"type": "integer", "default": 100},
                },
                "required": ["prompt"],
            },
            TaskTypeEnum.TXT2IMG: {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "negative_prompt": {"type": "string"},
                    "width": {"type": "integer", "default": 512},
                    "height": {"type": "integer", "default": 512},
                },
                "required": ["prompt", "negative_prompt"],
            },
            TaskTypeEnum.IMG2TXT: {
                "type": "object",
                "properties": {
                    "image": {"type": "string"},
                },
                "required": ["image"],
            },
            TaskTypeEnum.IMG2IMG: {
                "type": "object",
                "properties": {
                    "image": {"type": "string"},
                    "prompt": {"type": "string"},
                    "negative_prompt": {"type": "string"},
                    "strength": {"type": "number", "default": 0.8},
                    "width": {"type": "integer", "default": 512},
                    "height": {"type": "integer", "default": 512},
                },
                "required": ["image", "prompt", "negative_prompt"],
            },
            TaskTypeEnum.AUDIO2TXT: {
                "type": "object",
                "properties": {
                    "audio": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["audio"],
            },
            TaskTypeEnum.TXT2AUDIO: {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "voice": {"type": "string"},
                    "speed": {"type": "number", "default": 1.0},
                },
                "required": ["text"],
            },
            TaskTypeEnum.CLASSIFICATION: {
                "type": "object",
                "properties": {
                    "input": {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["input"],
            },
            TaskTypeEnum.OBJECT_DETECTION: {
                "type": "object",
                "properties": {
                    "image": {"type": "string"},
                    "confidence_threshold": {"type": "number", "default": 0.5},
                },
                "required": ["image"],
            },
            TaskTypeEnum.QUESTION_ANSWERING: {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["question", "context"],
            },
        }

        return schemas[self.value]

    def get_output_schema(self) -> Schema:
        schemas = {
            TaskTypeEnum.TXT2EMBED: {
                "type": "object",
                "properties": {
                    "embedding": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
            },
            TaskTypeEnum.TXT2TXT: {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
            },
            TaskTypeEnum.TXT2IMG: {
                "type": "object",
                "properties": {
                    "image_uri": {"type": "string"},
                },
            },
            TaskTypeEnum.IMG2TXT: {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
            },
            TaskTypeEnum.IMG2IMG: {
                "type": "object",
                "properties": {
                    "image_uri": {"type": "string"},
                },
            },
            TaskTypeEnum.AUDIO2TXT: {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "language": {"type": "string"},
                },
            },
            TaskTypeEnum.TXT2AUDIO: {
                "type": "object",
                "properties": {
                    "audio_uri": {"type": "string"},
                },
            },
            TaskTypeEnum.CLASSIFICATION: {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "score": {"type": "number"},
                    "scores": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "score": {"type": "number"},
                            },
                        },
                    },
                },
            },
            TaskTypeEnum.OBJECT_DETECTION: {
                "type": "object",
                "properties": {
                    "detections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "score": {"type": "number"},
                                "bbox": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "width": {"type": "number"},
                                        "height": {"type": "number"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            TaskTypeEnum.QUESTION_ANSWERING: {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "score": {"type": "number"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                },
            },
        }

        return schemas[self.value]
