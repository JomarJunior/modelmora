from typing import Annotated, Dict, Optional

import yaml
from pydantic import Field

from modelmora.registry.domain.locked_model_entry import LockedModelEntry
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_lock_id import ModelLockId
from modelmora.shared import BaseEntity
from modelmora.shared.custom_types import MediumString, ShortString


class ModelLock(BaseEntity):
    """The ModelLock entity provides reproducible deployment
    by locking specific model versions with their exact configurations and checksums.
    It's analogous to a package-lock.json file, ensuring consistent deployments across environments.
    """

    id: ModelLockId = Field(
        default_factory=ModelLockId.generate,
        description="The unique identifier for the model lock.",
    )

    name: Annotated[
        ShortString,
        Field(
            description="Human-readable name for the lock file.",
            examples=["production-lock", "staging-lock", "dev-lock"],
        ),
    ]

    description: Annotated[
        MediumString,
        Field(
            description="Detailed description of the lock file purpose.",
            examples=[
                "Lock file for production deployment of recommendation models.",
                "Staging environment lock for testing new model versions.",
            ],
        ),
    ]

    locked_models: Annotated[
        Dict[ModelId, LockedModelEntry],
        Field(
            description="A mapping of model IDs to their locked model entries.",
        ),
    ]

    environment: Annotated[
        Optional[ShortString],
        Field(
            description="The environment for which this lock file is intended (e.g., production, staging).",
            examples=["production", "staging", "development"],
        ),
    ] = None

    def add_locked_model(self, locked_model: LockedModelEntry) -> None:
        """Adds a locked model entry to the lock file.

        Args:
            locked_model (LockedModelEntry): The locked model entry to add.
        """
        self.locked_models[locked_model.model_id] = locked_model

    def remove_locked_model(self, model_id: ModelId) -> None:
        """Removes a locked model entry from the lock file by its model ID.

        Args:
            model_id (ModelId): The model ID of the locked model entry to remove.
        """
        if model_id in self.locked_models:
            del self.locked_models[model_id]

    def get_locked_version(self, model_id: ModelId) -> Optional[LockedModelEntry]:
        """Retrieves the locked model entry for a given model ID.

        Args:
            model_id (ModelId): The model ID to look up.
        Returns:
            Optional[LockedModelEntry]: The locked model entry if found, else None.
        """
        return self.locked_models.get(model_id)

    def model_dump_yaml(self) -> str:
        """Serializes the ModelLock entity to a YAML string.

        Returns:
            str: The YAML representation of the ModelLock entity.
        """
        return yaml.dump(self.model_dump(mode="json"))

    def __repr__(self) -> str:
        return (
            f"ModelLock(id={self.id}, name={self.name}, description={self.description}, "
            f"locked_models={self.locked_models}, environment={self.environment})"
        )

    def __str__(self) -> str:
        return f"ModelLock(name={self.name}, environment={self.environment})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelLock):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
