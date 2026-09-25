"""Real image generation via `diffusers` (R-2).

Only exercised on the Studio machine with the `gpu` extra installed; CI and the
component's own test suite run against the stand-ins in `runners/standin.py` instead
(FR-033, FR-034). Imports of `torch` and `diffusers` are deferred into the methods
that need them so importing this module never requires the GPU extra, mirroring
`runners/text.py`.
"""

from __future__ import annotations

import io
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
        self._footprint_bytes = 0

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
        from diffusers import StableDiffusionPipeline

        # Loaded with no safety checker attached: this runner reports a filter note
        # from whatever the pipeline itself declares at generation time (FR-008), and
        # a model whose weights ship none has nothing to disclose (filter_disclosure
        # "none" is the registry's matching judgment for such a model, T037a).
        pipeline = StableDiffusionPipeline.from_pretrained(
            self._model_path,
            torch_dtype=torch.float16,
            safety_checker=None,
            feature_extractor=None,
        )
        pipeline.set_progress_bar_config(disable=True)
        self._pipeline = pipeline.to(self._device)
        self._footprint_bytes = sum(
            parameter.numel() * parameter.element_size()
            for component in (
                self._pipeline.unet,
                self._pipeline.vae,
                self._pipeline.text_encoder,
            )
            for parameter in component.parameters()
        )

    def unload(self) -> None:
        if not self.is_loaded():
            return
        self._pipeline = None
        self._footprint_bytes = 0
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
