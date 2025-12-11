from typing import Annotated, Any, Dict, Optional

from pydantic import AnyUrl, Field

from modelmora.registry.domain.checksum import Checksum
from modelmora.registry.domain.framework_enum import FrameworkEnum
from modelmora.registry.domain.model_id import ModelId
from modelmora.registry.domain.model_version_id import ModelVersionId
from modelmora.registry.domain.resource_requirements import ResourceRequirements
from modelmora.shared import BaseEntity


class ModelVersion(BaseEntity):
    id: ModelVersionId = Field(
        default_factory=ModelVersionId.generate,
        description="The unique identifier for the model version.",
    )

    model_id: Annotated[
        ModelId,
        Field(
            description="The identifier of the model to which this version belongs.",
            examples=["laion/CLIP-ViT-H-14-laion2B-s32B-b79K", "openai/whisper-large-v2", "google/flan-t5-xxl"],
        ),
    ]

    value: Annotated[
        str,
        Field(
            description="The version string of the model version. In the format 'v{major}.{minor}.{patch}' or branch name",
            pattern=r"^(v\d+\.\d+\.\d+|[a-zA-Z0-9_\-]+)$",
            max_length=100,
            examples=["v1.0.0", "v2.1.3", "development", "feature-xyz"],
        ),
    ]

    checksum: Checksum

    artifact_uri: Annotated[
        AnyUrl,
        Field(
            description="The URI where the model artifacts are stored.",
            examples=[
                "s3://my-bucket/models/laion/CLIP-ViT-H-14-laion2B-s32B-b79K/v1.0.0/",
                "gs://my-bucket/models/openai/whisper-large-v2/v2.1.3/",
                "https://my-models.com/google/flan-t5-xxl/development/",
            ],
            frozen=True,
        ),
    ]

    resource_requirements: Annotated[
        ResourceRequirements,
        Field(
            description="The resource requirements for deploying the model version.",
        ),
    ]

    framework: Annotated[
        FrameworkEnum,
        Field(
            description="The machine learning framework used by the model version.",
        ),
    ]

    framework_version: Annotated[
        Optional[str],
        Field(
            pattern=r"^\d+(\.\d+){0,2}$",
            description="The version of the machine learning framework used by the model version.",
            examples=["2.4.1", "1.12.0", "0.9.1"],
            max_length=50,
        ),
    ] = None

    metadata: Annotated[
        Optional[Dict[str, Any]],
        Field(
            description="Additional metadata for the model version.",
        ),
    ] = None

    def update_metadata(self, new_metadata: Dict[str, Any]) -> None:
        """Update the metadata of the model version.

        Args:
            new_metadata (Dict[str, Any]): A dictionary containing the new metadata to be added or updated.
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata.update(new_metadata)

    def __repr__(self) -> str:
        return (
            f"ModelVersion(id={self.id}, model_id={self.model_id}, value={self.value}, "
            f"checksum={self.checksum}, artifact_uri={self.artifact_uri}, "
            f"resource_requirements={self.resource_requirements}, framework={self.framework}, "
            f"framework_version={self.framework_version}, metadata={self.metadata})"
        )

    def __str__(self) -> str:
        return f"{self.model_id}:{self.value}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return (
            self.id == other.id
            and self.model_id == other.model_id
            and self.value == other.value
            and self.checksum == other.checksum
            and self.artifact_uri == other.artifact_uri
            and self.resource_requirements == other.resource_requirements
            and self.framework == other.framework
            and self.framework_version == other.framework_version
            and self.metadata == other.metadata
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.id,
                self.model_id,
                self.value,
                self.checksum,
                self.artifact_uri,
                self.resource_requirements,
                self.framework,
                self.framework_version,
                frozenset(self.metadata.items()) if self.metadata else None,
            )
        )
