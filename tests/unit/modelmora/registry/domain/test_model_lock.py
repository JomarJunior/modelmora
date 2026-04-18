import pytest
import yaml
from pydantic import AnyUrl

from modelmora.registry.domain.locked_model_entry import LockedModelEntry
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_lock import ModelLock
from modelmora.registry.domain.resource_requirements import ResourceRequirements


class TestModelLockInitialization:
    """Test ModelLock initialization and validation."""

    def test_create_model_lock_with_valid_parameters_should_succeed(self) -> None:
        # Arrange
        locked_entry = LockedModelEntry(
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
        lock = ModelLock(
            name="production-lock",
            description="Lock file for production deployment",
            locked_models={ModelId(value="openai/gpt-4"): locked_entry},
        )

        # Assert
        assert lock.name == "production-lock"
        assert lock.description == "Lock file for production deployment"
        assert len(lock.locked_models) == 1
        assert ModelId(value="openai/gpt-4") in lock.locked_models
        assert lock.environment is None

    def test_create_model_lock_with_environment_should_succeed(self) -> None:
        # Arrange
        locked_entry = LockedModelEntry(
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
        lock = ModelLock(
            name="staging-lock",
            description="Lock file for staging environment",
            locked_models={ModelId(value="openai/gpt-4"): locked_entry},
            environment="staging",
        )

        # Assert
        assert lock.environment == "staging"

    def test_create_model_lock_with_empty_locked_models_should_succeed(self) -> None:
        # Arrange & Act
        lock = ModelLock(
            name="empty-lock",
            description="Empty lock file",
            locked_models={},
        )

        # Assert
        assert len(lock.locked_models) == 0

    def test_create_model_lock_should_generate_id(self) -> None:
        # Arrange & Act
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )

        # Assert
        assert lock.id is not None
        assert len(str(lock.id)) == 36  # UUID format


class TestModelLockAddLockedModel:
    """Test ModelLock add_locked_model method."""

    def test_add_locked_model_to_empty_lock_should_succeed(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )
        locked_entry = LockedModelEntry(
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
        lock.add_locked_model(locked_entry)

        # Assert
        assert len(lock.locked_models) == 1
        assert ModelId(value="openai/gpt-4") in lock.locked_models
        assert lock.locked_models[ModelId(value="openai/gpt-4")] == locked_entry

    def test_add_multiple_locked_models_should_succeed(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )
        entry1 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=ModelId(value="anthropic/claude"),
            model_version="v2.0.0",
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
        )

        # Act
        lock.add_locked_model(entry1)
        lock.add_locked_model(entry2)

        # Assert
        assert len(lock.locked_models) == 2
        assert ModelId(value="openai/gpt-4") in lock.locked_models
        assert ModelId(value="anthropic/claude") in lock.locked_models

    def test_add_locked_model_with_duplicate_model_id_should_overwrite(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )
        entry1 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=ModelId(value="openai/gpt-4"),
            model_version="v2.0.0",
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
        )

        # Act
        lock.add_locked_model(entry1)
        lock.add_locked_model(entry2)

        # Assert
        assert len(lock.locked_models) == 1
        assert lock.locked_models[ModelId(value="openai/gpt-4")].model_version == "v2.0.0"


class TestModelLockRemoveLockedModel:
    """Test ModelLock remove_locked_model method."""

    def test_remove_existing_locked_model_should_succeed(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={model_id: locked_entry},
        )

        # Act
        lock.remove_locked_model(model_id)

        # Assert
        assert len(lock.locked_models) == 0
        assert model_id not in lock.locked_models

    def test_remove_non_existing_locked_model_should_do_nothing(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={model_id: locked_entry},
        )
        non_existing_id = ModelId(value="anthropic/claude")

        # Act
        lock.remove_locked_model(non_existing_id)

        # Assert
        assert len(lock.locked_models) == 1
        assert model_id in lock.locked_models

    def test_remove_from_multiple_locked_models_should_remove_only_specified(
        self,
    ) -> None:
        # Arrange
        model_id1 = ModelId(value="openai/gpt-4")
        model_id2 = ModelId(value="anthropic/claude")
        entry1 = LockedModelEntry(
            model_id=model_id1,
            model_version="v1.0.0",
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
        )
        entry2 = LockedModelEntry(
            model_id=model_id2,
            model_version="v2.0.0",
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
        )
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={model_id1: entry1, model_id2: entry2},
        )

        # Act
        lock.remove_locked_model(model_id1)

        # Assert
        assert len(lock.locked_models) == 1
        assert model_id1 not in lock.locked_models
        assert model_id2 in lock.locked_models


class TestModelLockGetLockedVersion:
    """Test ModelLock get_locked_version method."""

    def test_get_existing_locked_version_should_return_entry(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={model_id: locked_entry},
        )

        # Act
        result = lock.get_locked_version(model_id)

        # Assert
        assert result == locked_entry

    def test_get_non_existing_locked_version_should_return_none(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={model_id: locked_entry},
        )
        non_existing_id = ModelId(value="anthropic/claude")

        # Act
        result = lock.get_locked_version(non_existing_id)

        # Assert
        assert result is None

    def test_get_locked_version_from_empty_lock_should_return_none(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )
        model_id = ModelId(value="openai/gpt-4")

        # Act
        result = lock.get_locked_version(model_id)

        # Assert
        assert result is None


class TestModelLockYamlSerialization:
    """Test ModelLock YAML serialization."""

    def test_model_dump_yaml_should_return_valid_yaml_string(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="production-lock",
            description="Production deployment lock",
            locked_models={model_id: locked_entry},
            environment="production",
        )

        # Act
        yaml_output = lock.model_dump_yaml()

        # Assert
        assert isinstance(yaml_output, str)
        assert "name:" in yaml_output
        assert "production" in yaml_output

    def test_model_dump_yaml_should_contain_all_required_fields(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock = ModelLock(
            name="staging-lock",
            description="Staging environment lock",
            locked_models={model_id: locked_entry},
            environment="staging",
        )

        # Act
        yaml_output = lock.model_dump_yaml()

        # Assert
        assert "staging" in yaml_output
        assert "description:" in yaml_output
        assert "locked_models:" in yaml_output

    def test_model_dump_yaml_with_empty_locked_models_should_succeed(self) -> None:
        # Arrange
        lock = ModelLock(
            name="empty-lock",
            description="Empty lock file",
            locked_models={},
        )

        # Act
        yaml_output = lock.model_dump_yaml()

        # Assert
        assert isinstance(yaml_output, str)
        assert "locked_models:" in yaml_output or "locked_models: {}" in yaml_output


class TestModelLockStringRepresentations:
    """Test ModelLock string representations."""

    def test_repr_should_return_detailed_string(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
            environment="development",
        )

        # Act
        result = repr(lock)

        # Assert
        assert "ModelLock" in result
        assert "id=" in result
        assert "name=" in result
        assert "description=" in result
        assert "locked_models=" in result
        assert "environment=" in result

    def test_str_should_return_readable_string(self) -> None:
        # Arrange
        lock = ModelLock(
            name="production-lock",
            description="Production deployment lock",
            locked_models={},
            environment="production",
        )

        # Act
        result = str(lock)

        # Assert
        assert result == "ModelLock(name=production-lock, environment=production)"

    def test_str_with_no_environment_should_show_none(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )

        # Act
        result = str(lock)

        # Assert
        assert result == "ModelLock(name=test-lock, environment=None)"


class TestModelLockEquality:
    """Test ModelLock equality and hashing."""

    def test_model_locks_with_same_id_should_be_equal(self) -> None:
        # Arrange
        model_id = ModelId(value="openai/gpt-4")
        locked_entry = LockedModelEntry(
            model_id=model_id,
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
        lock1 = ModelLock(
            name="lock1",
            description="First lock",
            locked_models={model_id: locked_entry},
        )
        # Create another lock with same ID by using model_copy to get around immutability
        lock2 = lock1.model_copy(update={"name": "lock2", "description": "Second lock", "locked_models": {}})

        # Act & Assert
        assert lock1.id == lock2.id
        assert lock1 == lock2

    def test_model_locks_with_different_ids_should_not_be_equal(self) -> None:
        # Arrange
        lock1 = ModelLock(
            name="lock1",
            description="First lock",
            locked_models={},
        )
        lock2 = ModelLock(
            name="lock2",
            description="Second lock",
            locked_models={},
        )

        # Act & Assert
        assert lock1 != lock2

    def test_model_lock_equality_with_non_lock_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )

        # Act
        result = lock.__eq__("not a lock")

        # Assert
        assert result == NotImplemented

    def test_model_lock_should_be_hashable(self) -> None:
        # Arrange
        lock = ModelLock(
            name="test-lock",
            description="Test lock file",
            locked_models={},
        )

        # Act & Assert
        assert hash(lock) is not None

    def test_model_locks_with_same_id_should_have_same_hash(self) -> None:
        # Arrange
        lock1 = ModelLock(
            name="lock1",
            description="First lock",
            locked_models={},
        )
        # Create another lock with same ID using model_copy
        lock2 = lock1.model_copy(update={"name": "lock2"})

        # Act & Assert
        assert hash(lock1) == hash(lock2)

    def test_model_lock_can_be_used_in_set(self) -> None:
        # Arrange
        lock1 = ModelLock(
            name="lock1",
            description="First lock",
            locked_models={},
        )
        lock2 = ModelLock(
            name="lock2",
            description="Second lock",
            locked_models={},
        )

        # Act
        lock_set = {lock1, lock2}

        # Assert
        assert len(lock_set) == 2
        assert lock1 in lock_set
        assert lock2 in lock_set
