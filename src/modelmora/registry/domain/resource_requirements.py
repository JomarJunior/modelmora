from modelmora.registry.domain.resource_capacity import ResourceCapacity
from modelmora.shared import BaseValue
from modelmora.shared.custom_types import NaturalNumber


class ResourceRequirements(BaseValue):
    """
    Represents the resource requirements for a particular task or process.

    Attributes:
        memory_mb (NaturalNumber): The amount of memory required in megabytes.
        gpu_vram_mb (NaturalNumber): The amount of GPU VRAM required in megabytes.
        cpu_threads (NaturalNumber): The number of CPU threads required.
        gpu_count (NaturalNumber): The number of GPUs required.
        min_memory_mb (NaturalNumber): The minimum amount of memory required in megabytes.
        disk_space_mb (NaturalNumber): The amount of disk space required in megabytes.
    """

    memory_mb: NaturalNumber
    gpu_vram_mb: NaturalNumber
    cpu_threads: NaturalNumber
    gpu_count: NaturalNumber
    min_memory_mb: NaturalNumber
    disk_space_mb: NaturalNumber

    def __repr__(self) -> str:
        return (
            f"ResourceRequirements(memory_mb={self.memory_mb}, "
            f"gpu_vram_mb={self.gpu_vram_mb}, "
            f"cpu_threads={self.cpu_threads}, "
            f"gpu_count={self.gpu_count}, "
            f"min_memory_mb={self.min_memory_mb}, "
            f"disk_space_mb={self.disk_space_mb})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceRequirements):
            return NotImplemented
        return (
            self.memory_mb == other.memory_mb
            and self.gpu_vram_mb == other.gpu_vram_mb
            and self.cpu_threads == other.cpu_threads
            and self.gpu_count == other.gpu_count
            and self.min_memory_mb == other.min_memory_mb
            and self.disk_space_mb == other.disk_space_mb
        )

    def __hash__(self) -> int:
        return hash(
            (self.memory_mb, self.gpu_vram_mb, self.cpu_threads, self.gpu_count, self.min_memory_mb, self.disk_space_mb)
        )

    def fits_in(self, capacity: ResourceCapacity) -> bool:
        """Check if the resource requirements fit within the given resource capacity."""
        return (
            self.memory_mb <= capacity["memory_mb"]
            and self.gpu_vram_mb <= capacity["gpu_vram_mb"]
            and self.cpu_threads <= capacity["cpu_threads"]
            and self.gpu_count <= capacity["gpu_count"]
            and self.disk_space_mb <= capacity["disk_space_mb"]
        )
