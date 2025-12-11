from typing import Annotated, Dict

from pydantic import Field

from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_version import ModelVersion
from modelmora.registry.domain.model_version_id import ModelVersionId
from modelmora.registry.domain.task_type import TaskType
from modelmora.shared import BaseEntity


class Model(BaseEntity):
    id: Annotated[
        ModelId,
        Field(
            description="The unique identifier for the model in the format {org}/{repo}.",
            examples=["openai/gpt-4", "google/flan-t5-xxl"],
        ),
    ]

    task_type: Annotated[
        TaskType,
        Field(
            description="The type of task the model is designed to perform.",
            examples=["txt2txt", "txt2img", "txt2embed"],
        ),
    ]

    versions: Annotated[
        Dict[ModelVersionId, ModelVersion],
        Field(
            description="A mapping of model version IDs to their corresponding ModelVersion entities.",
            min_length=1,
        ),
    ]

    def add_version(self, model_version: ModelVersion) -> None:
        """Adds a new model version to the model.

        Args:
            model_version (ModelVersion): The model version to add.
        """
        self.versions[model_version.id] = model_version

    def get_latest_version(self) -> ModelVersion:
        """Retrieves the latest model version based on semantic versioning.

        Returns:
            ModelVersion: The latest model version.
        """
        if not self.versions:
            raise ValueError("No versions available for this model.")

        # Assuming version strings are in the format 'v{major}.{minor}.{patch}'
        def version_key(mv: ModelVersion) -> tuple:
            if not mv.value.startswith("v"):
                return (float("-inf"),)  # Non-semantic versions are considered the oldest
            parts = mv.value.lstrip("v").split(".")
            return tuple(int(part) for part in parts)

        latest_version = max(self.versions.values(), key=version_key)
        return latest_version

    def get_version_by_semantic(self, version_str: str) -> ModelVersion:
        """Retrieves a model version by its semantic version string.

        Args:
            version_str (str): The semantic version string to look for.

        Returns:
            ModelVersion: The model version matching the given version string.
        """
        for mv in self.versions.values():
            if mv.value == version_str:
                return mv
        raise ValueError(f"Model version '{version_str}' not found.")

    def __repr__(self) -> str:
        return f"Model(id={self.id}, task_type={self.task_type}, versions={list(self.versions.keys())})"

    def __str__(self) -> str:
        return f"Model(id={self.id})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Model):
            return NotImplemented
        return self.id == other.id and self.task_type == other.task_type and self.versions == other.versions

    def __hash__(self) -> int:
        return hash(
            (
                self.id,
                self.task_type,
                frozenset(self.versions.items()),
            )
        )
