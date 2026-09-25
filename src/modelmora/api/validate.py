"""Request validation: resolve the model that will serve a request, or refuse.

A model named in the request is looked up exactly (name and version are both
required by the contract's `ModelRef`); an unnamed model resolves to the default for
the request's slot (FR-004). Images pick the `text_with_images` slot (FR-003).

Capability checks (T025) run before a request is ever queued: a size the chosen model
cannot produce is `invalid_request`; a model whose declared footprint alone exceeds
this Studio's GPU is `cannot_be_served_on_this_studio` (FR-011, spec Edge Cases).
"""

from __future__ import annotations

from modelmora.messages import ImageRequest, ModelRef, TextRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.defaults import ModelRegistry, RegisteredModel
from modelmora.runners.base import Runner
from modelmora.worker.residency import Residency


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


def check_image_capability(runner: Runner, request: ImageRequest, residency: Residency) -> None:
    """Refuses before queueing (US2 acceptance scenario 3, FR-011).

    Two distinct reasons: a footprint the GPU could never hold, even with nothing
    else resident, is `cannot_be_served_on_this_studio`; a size beyond what this
    particular model can produce is `invalid_request`.
    """
    footprint = runner.declared_footprint_bytes()
    if not residency.fits_alone(footprint):
        raise ModelMoraRefusal(
            "cannot_be_served_on_this_studio",
            detail=f"{runner.name} v{runner.version} needs more memory than this Studio's GPU has",
        )

    max_dimensions = runner.max_image_dimensions()
    if max_dimensions is not None:
        max_width, max_height = max_dimensions
        if request.size.width > max_width or request.size.height > max_height:
            raise ModelMoraRefusal(
                "invalid_request",
                detail=(
                    f"{runner.name} v{runner.version} cannot produce images larger than "
                    f"{max_width}x{max_height}, asked for "
                    f"{request.size.width}x{request.size.height}"
                ),
            )


def resolve_image_runner(
    registry: ModelRegistry,
    runners: dict[tuple[str, str], Runner],
    residency: Residency,
    request: ImageRequest,
) -> tuple[RegisteredModel, Runner]:
    """Resolves the model and its runner, checked and ready to queue (or refused)."""
    model = resolve_image_model(registry, request)
    runner = runners.get((model.name, model.version))
    if runner is None:
        raise ModelMoraRefusal(
            "model_unavailable", detail=f"{model.name} v{model.version} has no runner attached"
        )
    check_image_capability(runner, request, residency)
    return model, runner
