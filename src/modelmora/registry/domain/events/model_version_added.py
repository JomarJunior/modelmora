from modelmora.shared.events import DomainEvent


class ModelVersionAddedEvent(DomainEvent):
    @classmethod
    def from_model_version(cls, model, model_version) -> "ModelVersionAddedEvent":
        return cls(
            event_type="ModelVersionAdded",
            aggregate_id=str(model.id),
            aggregate_type="Model",
            payload={
                "model_id": str(model.id),
                "model_version_id": str(model_version.id),
                "model_version_value": model_version.value,
            },
            version=1,
        )
