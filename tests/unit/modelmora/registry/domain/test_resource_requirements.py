import pytest
from pydantic import ValidationError

from modelmora.registry.domain.resource_requirements import ResourceRequirements


class TestResourceRequirementsInitialization:
    """Test ResourceRequirements initialization and validation."""

    def test_create_resource_requirements_with_valid_values_should_succeed(
        self,
    ) -> None:
        # Arrange & Act
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Assert
        assert requirements.memory_mb == 1024
        assert requirements.gpu_vram_mb == 2048
        assert requirements.cpu_threads == 4
        assert requirements.gpu_count == 1
        assert requirements.min_memory_mb == 512
        assert requirements.disk_space_mb == 5000

    def test_create_resource_requirements_with_zero_values_should_succeed(
        self,
    ) -> None:
        # Arrange & Act
        requirements = ResourceRequirements(
            memory_mb=0,
            gpu_vram_mb=0,
            cpu_threads=0,
            gpu_count=0,
            min_memory_mb=0,
            disk_space_mb=0,
        )

        # Assert
        assert requirements.memory_mb == 0
        assert requirements.gpu_vram_mb == 0

    def test_create_resource_requirements_with_negative_memory_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ResourceRequirements(
                memory_mb=-1,
                gpu_vram_mb=2048,
                cpu_threads=4,
                gpu_count=1,
                min_memory_mb=512,
                disk_space_mb=5000,
            )

    def test_create_resource_requirements_without_required_fields_should_raise_error(
        self,
    ) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ResourceRequirements()


class TestResourceRequirementsStringRepresentation:
    """Test ResourceRequirements string representation."""

    def test_repr_should_return_detailed_string(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Act
        result = repr(requirements)

        # Assert
        assert "ResourceRequirements" in result
        assert "memory_mb=1024" in result
        assert "gpu_vram_mb=2048" in result
        assert "cpu_threads=4" in result
        assert "gpu_count=1" in result
        assert "min_memory_mb=512" in result
        assert "disk_space_mb=5000" in result


class TestResourceRequirementsEquality:
    """Test ResourceRequirements equality and hashing."""

    def test_equal_resource_requirements_with_same_values_should_be_equal(
        self,
    ) -> None:
        # Arrange
        req1 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        req2 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Act & Assert
        assert req1 == req2

    def test_different_resource_requirements_should_not_be_equal(self) -> None:
        # Arrange
        req1 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        req2 = ResourceRequirements(
            memory_mb=2048,
            gpu_vram_mb=4096,
            cpu_threads=8,
            gpu_count=2,
            min_memory_mb=1024,
            disk_space_mb=10000,
        )

        # Act & Assert
        assert req1 != req2

    def test_resource_requirements_equality_with_non_resource_requirements_should_return_not_implemented(
        self,
    ) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Act
        result = requirements.__eq__("not requirements")

        # Assert
        assert result == NotImplemented

    def test_equal_resource_requirements_should_have_equal_hashes(self) -> None:
        # Arrange
        req1 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        req2 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Act & Assert
        assert hash(req1) == hash(req2)

    def test_different_resource_requirements_should_have_different_hashes(
        self,
    ) -> None:
        # Arrange
        req1 = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        req2 = ResourceRequirements(
            memory_mb=2048,
            gpu_vram_mb=4096,
            cpu_threads=8,
            gpu_count=2,
            min_memory_mb=1024,
            disk_space_mb=10000,
        )

        # Act & Assert
        assert hash(req1) != hash(req2)


class TestResourceRequirementsFitsIn:
    """Test ResourceRequirements fits_in method."""

    def test_fits_in_with_exact_capacity_should_return_true(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 1024,
            "gpu_vram_mb": 2048,
            "cpu_threads": 4,
            "gpu_count": 1,
            "disk_space_mb": 5000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is True

    def test_fits_in_with_larger_capacity_should_return_true(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 2048,
            "gpu_vram_mb": 4096,
            "cpu_threads": 8,
            "gpu_count": 2,
            "disk_space_mb": 10000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is True

    def test_fits_in_with_insufficient_memory_should_return_false(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=2048,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 1024,
            "gpu_vram_mb": 4096,
            "cpu_threads": 8,
            "gpu_count": 2,
            "disk_space_mb": 10000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is False

    def test_fits_in_with_insufficient_gpu_vram_should_return_false(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=4096,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 2048,
            "gpu_vram_mb": 2048,
            "cpu_threads": 8,
            "gpu_count": 2,
            "disk_space_mb": 10000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is False

    def test_fits_in_with_insufficient_cpu_threads_should_return_false(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=8,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 2048,
            "gpu_vram_mb": 4096,
            "cpu_threads": 4,
            "gpu_count": 2,
            "disk_space_mb": 10000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is False

    def test_fits_in_with_insufficient_gpu_count_should_return_false(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=2,
            min_memory_mb=512,
            disk_space_mb=5000,
        )
        capacity = {
            "memory_mb": 2048,
            "gpu_vram_mb": 4096,
            "cpu_threads": 8,
            "gpu_count": 1,
            "disk_space_mb": 10000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is False

    def test_fits_in_with_insufficient_disk_space_should_return_false(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=10000,
        )
        capacity = {
            "memory_mb": 2048,
            "gpu_vram_mb": 4096,
            "cpu_threads": 8,
            "gpu_count": 2,
            "disk_space_mb": 5000,
        }

        # Act
        result = requirements.fits_in(capacity)

        # Assert
        assert result is False


class TestResourceRequirementsImmutability:
    """Test ResourceRequirements immutability (frozen=True)."""

    def test_modify_resource_requirements_field_should_raise_error(self) -> None:
        # Arrange
        requirements = ResourceRequirements(
            memory_mb=1024,
            gpu_vram_mb=2048,
            cpu_threads=4,
            gpu_count=1,
            min_memory_mb=512,
            disk_space_mb=5000,
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            requirements.memory_mb = 2048
