import pytest
from pydantic import AnyUrl, ValidationError

from modelmora.registry.domain.framework_enum import FrameworkEnum
from modelmora.registry.domain.model import Model
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_version import ModelVersion
from modelmora.registry.domain.resource_requirements import ResourceRequirements
from modelmora.registry.domain.task_type import TaskType
from modelmora.registry.domain.task_type_enum import TaskTypeEnum


class TestModelInitialization:
    """Test Model initialization."""

    def test_create_model_with_valid_parameters_should_succeed(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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

        # Act
        model = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Assert
        assert model.id.value == "openai/gpt-4"
        assert model.task_type.value == TaskTypeEnum.TXT2TXT
        assert version.id in model.versions
        assert model.versions[version.id] == version


class TestModelAddVersion:
    """Test Model add_version method."""

    def test_add_version_to_model_should_succeed(self) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )
        version2 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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

        # Act
        model.add_version(version2)

        # Assert
        assert version2.id in model.versions
        assert model.versions[version2.id] == version2

    def test_add_multiple_versions_should_store_all_by_id(self) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        version2 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="v1.0.0",
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
        model = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )

        # Act
        model.add_version(version2)

        # Assert
        # Both versions should be stored with their unique IDs
        assert len(model.versions) == 2
        assert version1.id in model.versions
        assert version2.id in model.versions


class TestModelGetLatestVersion:
    """Test Model get_latest_version method."""

    def test_get_latest_version_validates_min_length_constraint(self) -> None:
        # Arrange & Act & Assert
        # Model requires at least 1 version (min_length=1), so creating with empty dict should fail
        with pytest.raises(ValidationError, match="at least 1"):
            Model(
                id=ModelId(value="openai/gpt-4"),
                task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
                versions={},
            )

    def test_get_latest_version_from_model_with_one_version_should_return_that_version(
        self,
    ) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        result = model.get_latest_version()

        # Assert
        assert result == version

    def test_get_latest_version_should_return_highest_semantic_version(self) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        version2 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="v2.1.0",
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
        version3 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="v2.0.0",
            checksum="sha256:" + "c" * 64,
            artifact_uri=AnyUrl("https://example.com/model3.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1536,
                gpu_vram_mb=3072,
                cpu_threads=6,
                gpu_count=1,
                min_memory_mb=768,
                disk_space_mb=7500,
            ),
            framework=FrameworkEnum.PYTORCH,
        )
        model = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1, version2.id: version2, version3.id: version3},
        )

        # Act
        result = model.get_latest_version()

        # Assert
        assert result == version2  # v2.1.0 is highest

    def test_get_latest_version_with_non_semantic_versions_should_treat_as_oldest(
        self,
    ) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        version2 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="main",
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
        model = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1, version2.id: version2},
        )

        # Act
        result = model.get_latest_version()

        # Assert
        # Semantic version v1.0.0 should be returned as non-semantic "main" is treated as oldest
        assert result == version1


class TestModelGetVersionBySemantic:
    """Test Model get_version_by_semantic method."""

    def test_get_version_by_semantic_with_exact_match_should_return_version(
        self,
    ) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="v1.2.3",
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        result = model.get_version_by_semantic("v1.2.3")

        # Assert
        assert result == version

    def test_get_version_by_semantic_with_no_match_should_raise_error(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Model version 'v2.0.0' not found"):
            model.get_version_by_semantic("v2.0.0")


class TestModelStringRepresentations:
    """Test Model string representations."""

    def test_repr_should_return_detailed_string(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        result = repr(model)

        # Assert
        assert "Model" in result
        assert "id=" in result
        assert "task_type=" in result
        assert "versions=" in result

    def test_str_should_return_model_id(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        result = str(model)

        # Assert
        assert "Model(id=" in result


class TestModelEquality:
    """Test Model equality and hashing."""

    def test_equal_models_should_be_equal(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        model1 = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )
        model2 = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act & Assert
        assert model1 == model2

    def test_different_models_should_not_be_equal(self) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        version2 = ModelVersion(
            model_id=ModelId(value="anthropic/claude"),
            value="v1.0.0",
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
        model1 = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )
        model2 = Model(
            id=ModelId(value="anthropic/claude"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version2.id: version2},
        )

        # Act & Assert
        assert model1 != model2

    def test_model_equality_with_non_model_should_return_not_implemented(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        result = model.__eq__("not a model")

        # Assert
        assert result == NotImplemented

    def test_model_should_be_hashable(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act & Assert
        assert hash(model) is not None

    def test_model_can_be_used_in_set(self) -> None:
        # Arrange
        version1 = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
        model1 = Model(
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version1.id: version1},
        )
        version2 = ModelVersion(
            model_id=ModelId(value="anthropic/claude"),
            value="v1.0.0",
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
            id=ModelId(value="anthropic/claude"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version2.id: version2},
        )

        # Act
        model_set = {model1, model2, model1}

        # Assert
        assert len(model_set) == 2

    def test_model_can_be_used_as_dict_key(self) -> None:
        # Arrange
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
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
            id=ModelId(value="openai/gpt-4"),
            task_type=TaskType(value=TaskTypeEnum.TXT2TXT),
            versions={version.id: version},
        )

        # Act
        model_dict = {model: "Test Model"}

        # Assert
        assert model_dict[model] == "Test Model"
