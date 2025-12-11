import pytest
from pydantic import AnyUrl

from modelmora.registry.domain.events import (
    ModelRegisteredEvent,
    ModelUnregisteredEvent,
    ModelVersionAddedEvent,
)
from modelmora.registry.domain.exceptions.model_already_exists_exception import (
    ModelAlreadyExistsException,
)
from modelmora.registry.domain.exceptions.model_not_found_exception import (
    ModelNotFoundException,
)
from modelmora.registry.domain.framework_enum import FrameworkEnum
from modelmora.registry.domain.model import Model
from modelmora.registry.domain.model_catalog import ModelCatalog, ModelFilter
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_version import ModelVersion
from modelmora.registry.domain.resource_requirements import ResourceRequirements
from modelmora.registry.domain.task_type import TaskType
from modelmora.registry.domain.task_type_enum import TaskTypeEnum


class TestModelCatalogInitialization:
    """Test ModelCatalog initialization and validation."""

    def test_create_model_catalog_with_valid_parameters_should_succeed(self) -> None:
        # Arrange & Act
        catalog = ModelCatalog(
            name="default-catalog",
        )

        # Assert
        assert catalog.name == "default-catalog"
        assert len(catalog.models) == 0
        assert catalog.id is not None

    def test_create_model_catalog_should_generate_id(self) -> None:
        # Arrange & Act
        catalog = ModelCatalog(
            name="test-catalog",
        )

        # Assert
        assert catalog.id is not None
        assert len(str(catalog.id)) == 36  # UUID format

    def test_create_model_catalog_with_empty_models_should_succeed(self) -> None:
        # Arrange & Act
        catalog = ModelCatalog(
            name="empty-catalog",
            models={},
        )

        # Assert
        assert len(catalog.models) == 0


class TestModelCatalogRegisterModel:
    """Test ModelCatalog register_model method."""

    def test_register_model_to_empty_catalog_should_succeed(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        catalog.register_model(model)

        # Assert
        assert len(catalog.models) == 1
        assert model_id in catalog.models
        assert catalog.models[model_id] == model

    def test_register_model_should_emit_event(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        catalog.register_model(model)

        # Assert
        assert len(catalog.events) == 1
        event = catalog.events[0]
        assert isinstance(event, ModelRegisteredEvent)
        assert event.payload["model_id"] == str(model_id)

    def test_register_multiple_models_should_succeed(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )

        # Act
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Assert
        assert len(catalog.models) == 2
        assert model_id1 in catalog.models
        assert model_id2 in catalog.models
        assert len(catalog.events) == 2

    def test_register_duplicate_model_should_raise_exception(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        catalog.register_model(model)

        # Act & Assert
        with pytest.raises(ModelAlreadyExistsException):
            catalog.register_model(model)


class TestModelCatalogUnregisterModel:
    """Test ModelCatalog unregister_model method."""

    def test_unregister_existing_model_should_succeed(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        catalog.register_model(model)

        # Act
        catalog.unregister_model(model_id)

        # Assert
        assert len(catalog.models) == 0
        assert model_id not in catalog.models

    def test_unregister_model_should_emit_event(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        catalog.register_model(model)
        catalog.clear_events()  # Clear registration event

        # Act
        catalog.unregister_model(model_id)

        # Assert
        assert len(catalog.events) == 1
        event = catalog.events[0]
        assert isinstance(event, ModelUnregisteredEvent)
        assert event.payload["model_id"] == str(model_id)

    def test_unregister_non_existing_model_should_raise_exception(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        non_existing_id = ModelId(value="openai/gpt-4")

        # Act & Assert
        with pytest.raises(ModelNotFoundException):
            catalog.unregister_model(non_existing_id)

    def test_unregister_from_multiple_models_should_remove_only_specified(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        catalog.unregister_model(model_id1)

        # Assert
        assert len(catalog.models) == 1
        assert model_id1 not in catalog.models
        assert model_id2 in catalog.models


class TestModelCatalogAddVersionToModel:
    """Test ModelCatalog add_version_to_model method."""

    def test_add_version_to_existing_model_should_succeed(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model-v1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )
        catalog.register_model(model)

        version2 = ModelVersion(
            model_id=model_id,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model-v2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )

        # Act
        catalog.add_version_to_model(model_id, version2)

        # Assert
        assert len(catalog.models[model_id].versions) == 2
        assert version2.id in catalog.models[model_id].versions

    def test_add_version_to_model_should_emit_event(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model-v1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )
        catalog.register_model(model)
        catalog.clear_events()  # Clear registration event

        version2 = ModelVersion(
            model_id=model_id,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model-v2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )

        # Act
        catalog.add_version_to_model(model_id, version2)

        # Assert
        assert len(catalog.events) == 1
        event = catalog.events[0]
        assert isinstance(event, ModelVersionAddedEvent)
        assert event.payload["model_id"] == str(model_id)
        assert event.payload["model_version_value"] == "v2.0.0"

    def test_add_version_to_non_existing_model_should_raise_exception(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        non_existing_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=non_existing_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )

        # Act & Assert
        with pytest.raises(ModelNotFoundException):
            catalog.add_version_to_model(non_existing_id, version)


class TestModelCatalogGetModel:
    """Test ModelCatalog get_model method."""

    def test_get_existing_model_should_return_model(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        catalog.register_model(model)

        # Act
        result = catalog.get_model(model_id)

        # Assert
        assert result == model
        assert result.id == model_id

    def test_get_non_existing_model_should_raise_exception(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        non_existing_id = ModelId(value="openai/gpt-4")

        # Act & Assert
        with pytest.raises(ModelNotFoundException):
            catalog.get_model(non_existing_id)


class TestModelCatalogListModels:
    """Test ModelCatalog list_models method."""

    def test_list_models_without_filter_should_return_all_models(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        result = catalog.list_models()

        # Assert
        assert len(result) == 2
        assert model1 in result
        assert model2 in result

    def test_list_models_from_empty_catalog_should_return_empty_list(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")

        # Act
        result = catalog.list_models()

        # Assert
        assert len(result) == 0

    def test_list_models_with_task_type_filter_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="stable/diffusion")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        filter: ModelFilter = {"task_type": TaskTypeEnum.TXT2TXT.value}
        result = catalog.list_models(filter=filter)

        # Assert
        assert len(result) == 1
        assert model1 in result
        assert model2 not in result

    def test_list_models_with_framework_filter_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="stable/diffusion")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        filter: ModelFilter = {"framework": FrameworkEnum.PYTORCH.value}
        result = catalog.list_models(filter=filter)

        # Assert - both models use PYTORCH framework
        assert len(result) == 2
        assert model1 in result
        assert model2 in result

    def test_list_models_with_search_text_filter_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        filter: ModelFilter = {"search_text": "openai"}
        result = catalog.list_models(filter=filter)

        # Assert
        assert len(result) == 1
        assert model1 in result
        assert model2 not in result

    def test_list_models_with_min_version_filter_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        filter: ModelFilter = {"min_version": "v2.0.0"}
        result = catalog.list_models(filter=filter)

        # Assert
        assert len(result) == 1
        assert model2 in result
        assert model1 not in result

    def test_list_models_with_max_version_filter_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="anthropic/claude")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version2.id: version2},
        )
        catalog.register_model(model1)
        catalog.register_model(model2)

        # Act
        filter: ModelFilter = {"max_version": "v1.5.0"}
        result = catalog.list_models(filter=filter)

        # Assert
        assert len(result) == 1
        assert model1 in result
        assert model2 not in result

    def test_list_models_with_multiple_filters_should_return_filtered_models(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id1 = ModelId(value="openai/gpt-4")
        version1 = ModelVersion(
            model_id=model_id1,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model1.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model1 = Model(
            id=model_id1,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        model_id2 = ModelId(value="openai/gpt-3")
        version2 = ModelVersion(
            model_id=model_id2,
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/model2.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model2 = Model(
            id=model_id2,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version2.id: version2},
        )

        model_id3 = ModelId(value="anthropic/claude")
        version3 = ModelVersion(
            model_id=model_id3,
            value="v1.5.0",
            checksum="sha256:" + "c" * 64,
            artifact_uri=AnyUrl("https://example.com/model3.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=2048,
                gpu_vram_mb=4096,
                cpu_threads=8,
                gpu_count=2,
                min_memory_mb=1024,
                disk_space_mb=10000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model3 = Model(
            id=model_id3,
            task_type=TaskType(value=TaskTypeEnum.TXT2IMG),
            versions={version3.id: version3},
        )

        catalog.register_model(model1)
        catalog.register_model(model2)
        catalog.register_model(model3)

        # Act
        filter: ModelFilter = {
            "task_type": TaskTypeEnum.TXT2TXT.value,
            "framework": FrameworkEnum.PYTORCH.value,
            "search_text": "gpt-4",
        }
        result = catalog.list_models(filter=filter)

        # Assert
        assert len(result) == 1
        assert model1 in result
        assert model2 not in result
        assert model3 not in result


class TestModelCatalogStringRepresentations:
    """Test ModelCatalog string representations."""

    def test_repr_should_return_detailed_string(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        catalog.register_model(model)

        # Act
        result = repr(catalog)

        # Assert
        assert "ModelCatalog" in result
        assert "id=" in result
        assert "name=" in result
        assert "models=" in result
        assert "openai/gpt-4" in result

    def test_str_should_return_readable_string(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="production-catalog")

        # Act
        result = str(catalog)

        # Assert
        assert "ModelCatalog" in result
        assert "production-catalog" in result


class TestModelCatalogEquality:
    """Test ModelCatalog equality and hashing."""

    def test_model_catalogs_with_same_id_name_models_should_be_equal(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        catalog1 = ModelCatalog(name="test-catalog")
        catalog1.register_model(model)

        # Create catalog2 with same ID and content
        catalog2 = catalog1.model_copy(deep=True)

        # Act & Assert
        assert catalog1 == catalog2

    def test_model_catalogs_with_different_ids_should_not_be_equal(self) -> None:
        # Arrange
        catalog1 = ModelCatalog(name="catalog1")
        catalog2 = ModelCatalog(name="catalog2")

        # Act & Assert
        assert catalog1 != catalog2

    def test_model_catalog_equality_with_non_catalog_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")

        # Act
        result = catalog.__eq__("not a catalog")

        # Assert
        assert result == NotImplemented

    def test_model_catalog_should_be_hashable(self) -> None:
        # Arrange
        catalog = ModelCatalog(name="test-catalog")

        # Act & Assert
        assert hash(catalog) is not None

    def test_model_catalogs_with_same_content_should_have_same_hash(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        version = ModelVersion(
            model_id=model_id,
            value="v1.0.0",
            checksum="sha256:" + "a" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=model_id,
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        catalog1 = ModelCatalog(name="test-catalog")
        catalog1.register_model(model)

        # Create catalog2 with same content
        catalog2 = catalog1.model_copy(deep=True)

        # Act & Assert
        assert hash(catalog1) == hash(catalog2)

    def test_model_catalog_can_be_used_in_set(self) -> None:
        # Arrange
        catalog1 = ModelCatalog(name="catalog1")
        catalog2 = ModelCatalog(name="catalog2")

        # Act
        catalog_set = {catalog1, catalog2}

        # Assert
        assert len(catalog_set) == 2
        assert catalog1 in catalog_set
        assert catalog2 in catalog_set
