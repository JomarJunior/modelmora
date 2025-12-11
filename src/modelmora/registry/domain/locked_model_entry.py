from typing import Annotated

from pydantic import AnyUrl, Field

from modelmora.registry.domain.checksum import Checksum
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.resource_requirements import ResourceRequirements
from modelmora.shared import BaseValue


class LockedModelEntry(BaseValue):
    """Represents a locked model entry in a model lock file."""

    model_id: Annotated[
        ModelId,
        Field(
            description="The identifier of the locked model.",
        ),
    ]

    model_version: Annotated[
        str,
        Field(
            description="The version string of the locked model version.",
            pattern=r"^(v\d+\.\d+\.\d+|[a-zA-Z0-9_\-]+)$",
            max_length=100,
            examples=["v1.0.0", "v2.1.3", "development", "feature-xyz"],
        ),
    ]

    checksum: Checksum

    artifact_uri: Annotated[
        AnyUrl,
        Field(
            description="The URI where the locked model artifacts are stored.",
        ),
    ]

    resource_requirements: Annotated[
        ResourceRequirements,
        Field(
            description="The resource requirements for deploying the locked model version.",
        ),
    ]

    def __repr__(self) -> str:
        return (
            f"LockedModelEntry(model_id={self.model_id}, "
            f"model_version={self.model_version}, "
            f"checksum={self.checksum}, "
            f"artifact_uri={self.artifact_uri}, "
            f"resource_requirements={self.resource_requirements})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LockedModelEntry):
            return NotImplemented
        return (
            self.model_id == other.model_id
            and self.model_version == other.model_version
            and self.checksum == other.checksum
            and self.artifact_uri == other.artifact_uri
            and self.resource_requirements == other.resource_requirements
        )

    def __hash__(self) -> int:
        return hash((self.model_id, self.model_version, self.checksum, self.artifact_uri, self.resource_requirements))

    def __str__(self) -> str:
        return f"LockedModelEntry for model {self.model_id} " f"version {self.model_version}"
