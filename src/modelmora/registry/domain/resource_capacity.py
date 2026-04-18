from typing import TypedDict

from modelmora.shared.custom_types import NaturalNumber


class ResourceCapacity(TypedDict):
    """
    Represents the resource capacity available for a particular task or process.

    Attributes:
        memory_mb (NaturalNumber): The amount of memory available in megabytes.
        gpu_vram_mb (NaturalNumber): The amount of GPU VRAM available in megabytes.
        cpu_threads (NaturalNumber): The number of CPU threads available.
        gpu_count (NaturalNumber): The number of GPUs available.
        disk_space_mb (NaturalNumber): The amount of disk space available in megabytes.
    """

    memory_mb: NaturalNumber
    gpu_vram_mb: NaturalNumber
    cpu_threads: NaturalNumber
    gpu_count: NaturalNumber
    disk_space_mb: NaturalNumber
