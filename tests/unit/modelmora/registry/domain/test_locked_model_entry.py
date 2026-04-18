import pytest
from pydantic import AnyUrl, ValidationError

from modelmora.registry.domain.locked_model_entry import LockedModelEntry
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.resource_requirements import ResourceRequirements


class TestLockedModelEntryInitialization:
    """Test LockedModelEntry initialization and validation."""

    def test_create_locked_model_entry_with_valid_values_should_succeed(
        self,
    ) -> None:
        # Arrange & Act
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Assert
        assert entry.model_id.value == "openai/gpt-4"
        assert entry.model_version == "v1.0.0"
        assert entry.checksum == "sha256:" + "a" * 64
        assert str(entry.artifact_uri) == "https://example.com/model.tar.gz"
        assert entry.resource_requirements.memory_mb == 1024

    def test_create_locked_model_entry_with_development_version_should_succeed(
        self,
    ) -> None:
        # Arrange & Act
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="development",
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
        )

        # Assert
        assert entry.model_version == "development"

    def test_create_locked_model_entry_with_feature_branch_version_should_succeed(
        self,
    ) -> None:
        # Arrange & Act
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="feature-xyz",
            checksum="sha256:" + "c" * 64,
            artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
            resource_requirements=ResourceRequirements(
                memory_mb=1024,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            ),
        )

        # Assert
        assert entry.model_version == "feature-xyz"

    def test_create_locked_model_entry_with_invalid_checksum_format_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            LockedModelEntry(
                model_id=ModelId(value="openai/gpt-4"),
                model_version="v1.0.0",
                checksum="invalid_checksum",
                artifact_uri=AnyUrl("https://example.com/model.tar.gz"),
                resource_requirements=ResourceRequirements(
                    memory_mb=1024,
                    gpu_vram_mb=2048,
                    cpu_threads=4,
                    gpu_count=1,
                    min_memory_mb=512,
                    disk_space_mb=5000,
                ),
            )

    def test_create_locked_model_entry_with_invalid_version_pattern_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            LockedModelEntry(
                model_id=ModelId(value="openai/gpt-4"),
                model_version="invalid version!",
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
            )

    def test_create_locked_model_entry_with_version_exceeding_max_length_should_raise_error(
        self,
    ) -> None:
        # Arrange
        long_version = "v" + "1" * 150

        # Act & Assert
        with pytest.raises(ValidationError):
            LockedModelEntry(
                model_id=ModelId(value="openai/gpt-4"),
                model_version=long_version,
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
            )


class TestLockedModelEntryStringRepresentations:
    """Test LockedModelEntry string representations."""

    def test_repr_should_return_detailed_string(self) -> None:
        # Arrange
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act
        result = repr(entry)

        # Assert
        assert "LockedModelEntry" in result
        assert "model_id" in result
        assert "model_version" in result
        assert "checksum" in result
        assert "artifact_uri" in result
        assert "resource_requirements" in result

    def test_str_should_return_readable_string(self) -> None:
        # Arrange
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act
        result = str(entry)

        # Assert
        assert "LockedModelEntry for model" in result
        assert "openai/gpt-4" in result
        assert "version v1.0.0" in result


class TestLockedModelEntryEquality:
    """Test LockedModelEntry equality and hashing."""

    def test_equal_locked_model_entries_with_same_values_should_be_equal(
        self,
    ) -> None:
        # Arrange
        entry1 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act & Assert
        assert entry1 == entry2

    def test_different_locked_model_entries_should_not_be_equal(self) -> None:
        # Arrange
        entry1 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=ModelId(value="anthropic/claude"),
            model_version="v2.0.0",
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
        )

        # Act & Assert
        assert entry1 != entry2

    def test_locked_model_entry_equality_with_non_entry_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act
        result = entry.__eq__("not an entry")

        # Assert
        assert result == NotImplemented

    def test_equal_locked_model_entries_should_have_equal_hashes(self) -> None:
        # Arrange
        entry1 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act & Assert
        assert hash(entry1) == hash(entry2)


class TestLockedModelEntryImmutability:
    """Test LockedModelEntry immutability (frozen=True)."""

    def test_modify_locked_model_entry_field_should_raise_error(self) -> None:
        # Arrange
        entry = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            entry.model_version = "v2.0.0"
