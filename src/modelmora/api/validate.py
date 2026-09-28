"""Request validation: resolve the model that will serve a request, or refuse.

A model named in the request is looked up exactly (name and version are both
required by the contract's `ModelRef`); an unnamed model resolves to the default for
the request's slot (FR-004). Images pick the `text_with_images` slot (FR-003).

Capability checks (T025) run before a request is ever queued: a size the chosen model
cannot produce is `invalid_request`; a model whose declared footprint alone exceeds
this Studio's GPU is `cannot_be_served_on_this_studio` (FR-011, spec Edge Cases). T063
folds a request's own runtime overhead (SDXL activations at the requested size) into
that footprint, so a pair that would not truly fit is never loaded together. T065
and T066 add two more before-queueing checks: a conversation that could never fit the
chosen model's context window, and a size not a multiple of 8 (every SDXL/SD-family
VAE's own downsampling factor).
"""

from __future__ import annotations

from modelmora.messages import ImageRequest, ModelRef, TextRequest
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.registry import ModelRegistry, RegisteredModel
from modelmora.runners.base import Runner
from modelmora.runners.llamacpp import DEFAULT_MAX_TOKENS
from modelmora.worker.residency import Residency

# A deliberately generous heuristic (real English text tokenizes to noticeably fewer
# tokens per character than this in practice): the point is to refuse a request that
# could never fit, not to size generation exactly -- FR-007 forbids silently shrinking
# what was asked, so this must never be tight enough to refuse something that would
# actually have fit.
_CHARS_PER_TOKEN_ESTIMATE = 4


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


def check_loadable(runner: Runner, residency: Residency) -> None:
    """Refuses before queueing a model whose load already failed in this process
    (T072, spec Edge Cases): `model_unavailable` now, rather than accepted only to
    retry a load known to fail. No other model is used in its place (FR-007)."""
    if residency.is_unloadable(runner):
        raise ModelMoraRefusal(
            "model_unavailable",
            detail=f"{runner.name} v{runner.version} could not be loaded on this Studio",
        )


def check_text_capability(runner: Runner, request: TextRequest) -> None:
    """Refuses before queueing (T065, FR-007, FR-011).

    A runner with no fixed context window (the stand-ins, `TextRunner`) has nothing
    to check here. `LlamaCppTextRunner` does: a conversation plus the requested
    output length that could never fit its context is refused now, rather than
    accepted and left to fail or be silently truncated mid-generation.
    """
    context_window = runner.context_window_tokens()
    if context_window is None:
        return
    conversation_chars = sum(len(turn.text) for turn in request.conversation or [])
    prompt_chars = len(request.instructions) + conversation_chars
    settings = request.settings
    requested_output_tokens = (settings.maxLength if settings else None) or DEFAULT_MAX_TOKENS
    estimated_prompt_tokens = prompt_chars // _CHARS_PER_TOKEN_ESTIMATE + 1
    if estimated_prompt_tokens + requested_output_tokens > context_window:
        raise ModelMoraRefusal(
            "invalid_request",
            detail=(
                f"{runner.name} v{runner.version}'s context window ({context_window} tokens) "
                f"cannot hold this conversation and the requested output length"
            ),
        )


def check_image_capability(runner: Runner, request: ImageRequest, residency: Residency) -> int:
    """Refuses before queueing (US2 acceptance scenario 3, FR-011); returns the
    footprint this request would need, for the worker to reserve at admission
    (T063, `worker/residency.py`'s `footprint_override`).

    Two distinct reasons: a footprint the GPU could never hold, even with nothing
    else resident, is `cannot_be_served_on_this_studio`; a size beyond what this
    particular model can produce, or not a multiple of 8 (every SDXL/SD-family VAE's
    own downsampling factor, T066), is `invalid_request`.
    """
    if request.size.width % 8 or request.size.height % 8:
        raise ModelMoraRefusal(
            "invalid_request",
            detail=(
                f"width and height must be multiples of 8, got "
                f"{request.size.width}x{request.size.height}"
            ),
        )

    footprint = runner.footprint_bytes_for_image(
        width=request.size.width, height=request.size.height
    )
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
    return footprint


def resolve_image_runner(
    registry: ModelRegistry,
    runners: dict[tuple[str, str], Runner],
    residency: Residency,
    request: ImageRequest,
) -> tuple[RegisteredModel, Runner, int]:
    """Resolves the model and its runner, checked and ready to queue (or refused);
    the footprint is what the worker reserves at admission (T063)."""
    model = resolve_image_model(registry, request)
    runner = runners.get((model.name, model.version))
    if runner is None:
        raise ModelMoraRefusal(
            "model_unavailable", detail=f"{model.name} v{model.version} has no runner attached"
        )
    check_loadable(runner, residency)
    footprint = check_image_capability(runner, request, residency)
    return model, runner, footprint
