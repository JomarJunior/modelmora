import pytest
from pydantic import AnyUrl, ValidationError

from modelmora.registry.domain.framework_enum import FrameworkEnum
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_version import ModelVersion
from modelmora.registry.domain.resource_requirements import ResourceRequirements


class TestModelVersionInitialization:
    """Test ModelVersion initialization and validation."""

    def test_create_model_version_with_valid_values_should_succeed(self) -> None:
        # Arrange & Act
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
            framework_version="2.4.1",
        )

        # Assert
        assert version.model_id.value == "openai/gpt-4"
        assert version.value == "v1.0.0"
        assert version.framework == FrameworkEnum.PYTORCH
        assert version.framework_version == "2.4.1"
        assert version.metadata is None

    def test_create_model_version_with_metadata_should_succeed(self) -> None:
        # Arrange & Act
        metadata = {"author": "OpenAI", "license": "MIT"}
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
            metadata=metadata,
        )

        # Assert
        assert version.metadata == metadata

    def test_create_model_version_with_branch_name_should_succeed(self) -> None:
        # Arrange & Act
        version = ModelVersion(
            model_id=ModelId(value="openai/gpt-4"),
            value="development",
            checksum="sha256:" + "b" * 64,
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

        # Assert
        assert version.value == "development"

    def test_create_model_version_with_invalid_version_pattern_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelVersion(
                model_id=ModelId(value="openai/gpt-4"),
                value="invalid version!",
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

    def test_create_model_version_with_invalid_framework_version_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ModelVersion(
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
                framework_version="invalid.version.x",
            )


class TestModelVersionUpdateMetadata:
    """Test ModelVersion update_metadata method."""

    def test_update_metadata_on_version_without_metadata_should_create_metadata(
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

        # Act
        version.update_metadata({"author": "OpenAI"})

        # Assert
        assert version.metadata == {"author": "OpenAI"}

    def test_update_metadata_on_version_with_existing_metadata_should_merge(
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
            metadata={"author": "OpenAI"},
        )

        # Act
        version.update_metadata({"license": "MIT", "version": "1.0"})

        # Assert
        assert version.metadata == {"author": "OpenAI", "license": "MIT", "version": "1.0"}

    def test_update_metadata_should_overwrite_existing_keys(self) -> None:
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
            metadata={"author": "OpenAI", "version": "1.0"},
        )

        # Act
        version.update_metadata({"version": "2.0"})

        # Assert
        assert version.metadata["version"] == "2.0"


class TestModelVersionStringRepresentations:
    """Test ModelVersion string representations."""

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

        # Act
        result = repr(version)

        # Assert
        assert "ModelVersion" in result
        assert "model_id" in result
        assert "value" in result

    def test_str_should_return_readable_string(self) -> None:
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
        result = str(version)

        # Assert
        assert result == "openai/gpt-4:v1.0.0"


class TestModelVersionEquality:
    """Test ModelVersion equality and hashing."""

    def test_equal_model_versions_with_same_values_should_have_different_ids(self) -> None:
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
        # IDs are generated uniquely, so they won't be equal even with same content
        assert version1.id != version2.id
        # Since IDs differ and equality checks ID, they won't be equal
        assert version1 != version2

    def test_different_model_versions_should_not_be_equal(self) -> None:
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
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/other.tar.gz"),
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

        # Act & Assert
        assert version1 != version2

    def test_model_version_equality_with_non_version_should_return_not_implemented(
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

        # Act
        result = version.__eq__("not a version")

        # Assert
        assert result == NotImplemented

    def test_model_version_should_be_hashable(self) -> None:
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

        # Act & Assert
        assert hash(version) is not None

    def test_model_version_can_be_used_in_set(self) -> None:
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
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/other.tar.gz"),
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
        version_set = {version1, version2, version1}

        # Assert
        assert len(version_set) == 2

    def test_model_version_can_be_used_as_dict_key(self) -> None:
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
            value="v2.0.0",
            checksum="sha256:" + "b" * 64,
            artifact_uri=AnyUrl("https://example.com/other.tar.gz"),
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
        version_dict = {version1: "First Version", version2: "Second Version"}

        # Assert
        assert version_dict[version1] == "First Version"
        assert version_dict[version2] == "Second Version"
