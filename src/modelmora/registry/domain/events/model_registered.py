from modelmora.shared.events import DomainEvent


class ModelRegisteredEvent(DomainEvent):
    @classmethod
    def from_model(cls, model) -> "ModelRegisteredEvent":
        return cls(
            event_type="ModelRegistered",
            aggregate_id=str(model.id),
            aggregate_type="Model",
            payload={
                "model_id": str(model.id),
                "task_type": str(model.task_type),
                "versions": [str(mv.id) for mv in model.versions.values()],
            },
            version=1,
        )
