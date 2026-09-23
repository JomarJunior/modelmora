"""Request validation: resolve the model that will serve a request, or refuse.

A model named in the request is looked up exactly (name and version are both
required by the contract's `ModelRef`); an unnamed model resolves to the default for
the request's slot (FR-004). Images pick the `text_with_images` slot (FR-003).
"""

from __future__ import annotations

from modelmora.messages import ImageRequest, ModelRef, TextRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.defaults import ModelRegistry, RegisteredModel


def resolve_text_model(registry: ModelRegistry, request: TextRequest) -> RegisteredModel:
    has_images = bool(request.images)

    if request.model is not None:
        model = registry.resolve(request.model.name, request.model.version)
        if model is None:
            raise ModelMoraRefusal(
                "unknown_model",
                detail=f"no model on record named {request.model.name!r} "
                f"version {request.model.version!r}",
            )
        if has_images and not model.reads_images:
            raise ModelMoraRefusal(
                "invalid_request",
                detail=f"{model.name} v{model.version} cannot read images",
            )
        return model

    slot = "text_with_images" if has_images else "text"
    model = registry.default_for_slot(slot)
    if model is None:
        if has_images:
            raise ModelMoraRefusal("invalid_request", detail="no model on record can read images")
        raise ModelMoraRefusal("model_unavailable", detail="no default text model on record")
    return model


def resolve_image_model(registry: ModelRegistry, request: ImageRequest) -> RegisteredModel:
    if request.model is not None:
        model = registry.resolve(request.model.name, request.model.version)
        if model is None:
            raise ModelMoraRefusal(
                "unknown_model",
                detail=f"no model on record named {request.model.name!r} "
                f"version {request.model.version!r}",
            )
        return model

    model = registry.default_for_slot("image")
    if model is None:
        raise ModelMoraRefusal("model_unavailable", detail="no default image model on record")
    return model


def model_ref(model: RegisteredModel) -> ModelRef:
    return ModelRef(name=model.name, version=model.version)
