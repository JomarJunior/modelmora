from modelmora.shared.events import DomainEvent


class ModelUnregisteredEvent(DomainEvent):
    @classmethod
    def from_model(cls, model) -> "ModelUnregisteredEvent":
        return cls(
            event_type="ModelUnregistered",
            aggregate_id=str(model.id),
            aggregate_type="Model",
            payload={
                "model_id": str(model.id),
                "task_type": str(model.task_type),
                "versions": [str(mv.id) for mv in model.versions.values()],
            },
            version=1,
        )
