from typing import Annotated, Collection, Dict, Optional, TypedDict

from pydantic import Field

from modelmora.registry.domain.events import ModelRegisteredEvent, ModelUnregisteredEvent, ModelVersionAddedEvent
from modelmora.registry.domain.exceptions.model_already_exists_exception import ModelAlreadyExistsException
from modelmora.registry.domain.exceptions.model_not_found_exception import ModelNotFoundException
from modelmora.registry.domain.model import Model, ModelId
from modelmora.registry.domain.model_catalog_id import ModelCatalogId
from modelmora.registry.domain.model_version import ModelVersion
from modelmora.shared import BaseAggregate
from modelmora.shared.custom_types import ShortString


class ModelFilter(TypedDict, total=False):
    task_type: str
    framework: str
    min_version: str
    max_version: str
    search_text: str


class ModelCatalog(BaseAggregate):
    """The ModelCatalog aggregate manages the collection of registered models and enforces consistency boundaries for model registration, versioning, and catalog operations."""

    id: ModelCatalogId = Field(
        default_factory=ModelCatalogId.generate,
        description="The unique identifier for the model catalog.",
    )

    name: Annotated[
        ShortString,
        Field(
            description="Catalog name for easy identification.",
            examples=["default-catalog", "vision-models", "nlp-models"],
        ),
    ]

    models: Dict[ModelId, Model] = Field(
        default_factory=dict,
        description="A mapping of model IDs to their corresponding Model entities in the catalog.",
    )

    def register_model(self, model: Model) -> None:
        """Registers a new model in the catalog.

        Args:
            model (Model): The model to register.
        """
        # Validate model doesn't exist
        if model.id in self.models:
            raise ModelAlreadyExistsException(model.id)

        self.models[model.id] = model

        # Generate event
        self.emit_event(ModelRegisteredEvent.from_model(model))

    def unregister_model(self, model_id: ModelId) -> None:
        """Unregisters a model from the catalog.

        Args:
            model_id (ModelId): The ID of the model to unregister.
        """
        # Validate model exists
        if model_id not in self.models:
            raise ModelNotFoundException(model_id)

        old_model = self.models[model_id].model_copy()
        del self.models[model_id]

        # Generate event
        self.emit_event(ModelUnregisteredEvent.from_model(old_model))

    def add_version_to_model(self, model_id: ModelId, model_version: ModelVersion) -> None:
        """Adds a new version to an existing model in the catalog.

        Args:
            model_id (ModelId): The ID of the model to which the version will be added.
            model_version (ModelVersion): The model version to add.
        """
        # Validate model exists
        if model_id not in self.models:
            raise ModelNotFoundException(model_id)

        model = self.models[model_id]
        model.add_version(model_version)

        # Generate event
        self.emit_event(ModelVersionAddedEvent.from_model_version(model, model_version))

    def get_model(self, model_id: ModelId) -> Model:
        """Retrieves a model from the catalog by its ID.

        Args:
            model_id (ModelId): The ID of the model to retrieve.
        Returns:
            Model: The model with the specified ID.
        """
        if model_id not in self.models:
            raise ModelNotFoundException(model_id)

        return self.models[model_id]

    def list_models(self, filter: Optional[ModelFilter] = None) -> Collection[Model]:
        """Lists models in the catalog, optionally filtered by criteria.

        Args:
            filter (Optional[ModelFilter]): An optional filter to apply to the model listing.
        Returns:
            Collection[Model]: A collection of models matching the filter criteria.
        """

        models = list(self.models.values())

        if filter is None:
            # No filter applied, return all models
            return models

        # Apply filters
        filter_task_type = filter.get("task_type")
        if filter_task_type:
            models = [m for m in models if m.task_type.value == filter_task_type]

        filter_framework = filter.get("framework")
        if filter_framework:
            models = [m for m in models if any(mv.framework == filter_framework for mv in m.versions.values())]

        filter_search_text = filter.get("search_text")
        if filter_search_text:
            search_text = filter_search_text.lower()
            models = [m for m in models if search_text in m.id.value.lower()]

        filter_min_version = filter.get("min_version")
        if filter_min_version:
            models = [m for m in models if any(mv.value >= filter_min_version for mv in m.versions.values())]

        filter_max_version = filter.get("max_version")
        if filter_max_version:
            models = [m for m in models if any(mv.value <= filter_max_version for mv in m.versions.values())]

        return models

    def __repr__(self) -> str:
        return f"ModelCatalog(id={self.id}, name={self.name}, models={list(self.models.keys())})"

    def __str__(self) -> str:
        return f"ModelCatalog(id={self.id}, name={self.name})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelCatalog):
            return NotImplemented
        return self.id == other.id and self.name == other.name and self.models == other.models

    def __hash__(self) -> int:
        return hash(
            (
                self.id,
                self.name,
                frozenset(self.models.items()),
            )
        )
