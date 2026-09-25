"""Real image generation via `diffusers` (R-2).

Only exercised on the Studio machine with the `gpu` extra installed; CI and the
component's own test suite run against the stand-ins in `runners/standin.py` instead
(FR-033, FR-034). Imports of `torch` and `diffusers` are deferred into the methods
that need them so importing this module never requires the GPU extra, mirroring
`runners/text.py`.

`model_path` may name a `diffusers`-layout directory (`from_pretrained`, the original
shape of this runner) or a single checkpoint file (`from_single_file`, the spec 002
amendment, T059, for the Studio's own SDXL-architecture collection): which one is used
is decided by whether the path is a file or a directory, not declared separately,
since every single-file checkpoint this Studio has recorded is SDXL and every
directory one is SD1.5-architecture (`StableDiffusionPipeline`). A model that broke
that pattern would need this runner taught an explicit architecture hint; none does
yet.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from modelmora.runners.base import GeneratedImage, Runner


class ImageRunner(Runner):
    """A `diffusers` text-to-image pipeline, loaded and unloaded on demand."""

    kind = "image"

    def __init__(
        self,
        *,
        name: str,
        version: str,
        model_path: str,
        max_width: int | None = None,
        max_height: int | None = None,
        default_steps: int = 30,
        default_guidance: float = 7.5,
        device: str = "cuda",
        declared_footprint_bytes: int | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.reads_images = False
        self._model_path = model_path
        self._device = device
        self._max_width = max_width
        self._max_height = max_height
        self._default_steps = default_steps
        self._default_guidance = default_guidance
        self._pipeline: Any = None
        # See the matching comment in `runners/text.py`: `declared_footprint_bytes()`
        # is asked before `load()` (FR-009, FR-011), so a real pipeline needs a hint
        # to report before its weights are actually resident.
        self._declared_footprint_bytes = declared_footprint_bytes
        self._footprint_bytes = declared_footprint_bytes or 0

    def declared_footprint_bytes(self) -> int:
        return self._footprint_bytes

    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def max_image_dimensions(self) -> tuple[int, int] | None:
        if self._max_width is None or self._max_height is None:
            return None
        return (self._max_width, self._max_height)

    def load(self) -> None:
        if self.is_loaded():
            return
        import torch
        from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

        is_single_file = Path(self._model_path).is_file()
        pipeline_cls = StableDiffusionXLPipeline if is_single_file else StableDiffusionPipeline
        # Loaded with no safety checker attached: this runner reports a filter note
        # from whatever the pipeline itself declares at generation time (FR-008), and
        # a model whose weights ship none has nothing to disclose (filter_disclosure
        # "none" is the registry's matching judgment for such a model, T037a).
        no_filter_kwargs = (
            {} if is_single_file else {"safety_checker": None, "feature_extractor": None}
        )
        load_fn = pipeline_cls.from_single_file if is_single_file else pipeline_cls.from_pretrained
        pipeline = load_fn(self._model_path, torch_dtype=torch.float16, **no_filter_kwargs)
        pipeline.set_progress_bar_config(disable=True)
        self._pipeline = pipeline.to(self._device)
        text_encoders = [self._pipeline.text_encoder]
        if hasattr(self._pipeline, "text_encoder_2") and self._pipeline.text_encoder_2 is not None:
            text_encoders.append(self._pipeline.text_encoder_2)
        self._footprint_bytes = sum(
            parameter.numel() * parameter.element_size()
            for component in (self._pipeline.unet, self._pipeline.vae, *text_encoders)
            for parameter in component.parameters()
        )

    def unload(self) -> None:
        if not self.is_loaded():
            return
        self._pipeline = None
        self._footprint_bytes = self._declared_footprint_bytes or 0
        import gc

        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def generate_image(
        self,
        *,
        description: str,
        avoid: str | None = None,
        width: int,
        height: int,
        seed: int | None = None,
        steps: int | None = None,
        guidance: float | None = None,
    ) -> GeneratedImage:
        if not self.is_loaded():
            raise RuntimeError(f"{self.name} v{self.version} is not loaded")

        import torch

        generator = None
        if seed is not None:
            generator = torch.Generator(device=self._device).manual_seed(seed)

        used_steps = steps or self._default_steps
        used_guidance = guidance if guidance is not None else self._default_guidance
        result = self._pipeline(
            prompt=description,
            negative_prompt=avoid,
            width=width,
            height=height,
            num_inference_steps=used_steps,
            guidance_scale=used_guidance,
            generator=generator,
        )
        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        # Not every pipeline reports this; `getattr` keeps a model with no such
        # attribute silently filter-free rather than raising (FR-008).
        filter_note = None
        nsfw_flags = getattr(result, "nsfw_content_detected", None)
        if nsfw_flags and any(nsfw_flags):
            filter_note = (
                f"{self.name} v{self.version}'s built-in safety filter changed this output"
            )

        settings_used: dict[str, Any] = {
            "seed": seed,
            "steps": used_steps,
            "guidance": used_guidance,
            "width": width,
            "height": height,
        }
        return GeneratedImage(
            png_bytes=buffer.getvalue(), settings_used=settings_used, filter_note=filter_note
        )
