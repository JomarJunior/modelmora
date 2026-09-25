"""Deterministic stand-in runners with no GPU (FR-033, FR-034, R-10).

Used by the queue and API test suites so eviction, bounded overtaking, busy refusals
and shutdown are all exercised without a GPU, and by the API smoke tests so the
service can be proven end to end before a real model exists.
"""

from __future__ import annotations

import hashlib
import io
import time
from typing import Any

from PIL import Image

from modelmora.runners.base import GeneratedImage, GeneratedText, Runner


class StandInTextRunner(Runner):
    kind = "text"

    def __init__(
        self,
        *,
        name: str,
        version: str,
        reads_images: bool = False,
        fake_load_seconds: float = 0.0,
        fake_footprint_bytes: int = 256 * 1024 * 1024,
        filter_note: str | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.reads_images = reads_images
        self._fake_load_seconds = fake_load_seconds
        self._fake_footprint_bytes = fake_footprint_bytes
        self._filter_note = filter_note
        self._loaded = False

    def declared_footprint_bytes(self) -> int:
        return self._fake_footprint_bytes

    def load(self) -> None:
        if self._loaded:
            return
        if self._fake_load_seconds:
            time.sleep(self._fake_load_seconds)
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def generate_text(
        self,
        *,
        instructions: str,
        conversation: list[dict[str, str]] | None = None,
        images: list[bytes] | None = None,
        seed: int | None = None,
        max_length: int | None = None,
        temperature: float | None = None,
    ) -> GeneratedText:
        if images and not self.reads_images:
            raise ValueError(f"{self.name} cannot read images")
        body = f"[{self.name} v{self.version} seed={seed}] {instructions}"
        if images:
            body += f" (with {len(images)} image(s))"
        text = body if max_length is None else body[:max_length]
        settings_used: dict[str, Any] = {
            "seed": seed,
            "maxLength": max_length,
            "temperature": temperature,
        }
        return GeneratedText(text=text, settings_used=settings_used, filter_note=self._filter_note)


class StandInImageRunner(Runner):
    kind = "image"

    def __init__(
        self,
        *,
        name: str,
        version: str,
        fake_load_seconds: float = 0.0,
        fake_footprint_bytes: int = 512 * 1024 * 1024,
        filter_note: str | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.reads_images = False
        self._fake_load_seconds = fake_load_seconds
        self._fake_footprint_bytes = fake_footprint_bytes
        self._filter_note = filter_note
        self._max_width = max_width
        self._max_height = max_height
        self._loaded = False

    def declared_footprint_bytes(self) -> int:
        return self._fake_footprint_bytes

    def load(self) -> None:
        if self._loaded:
            return
        if self._fake_load_seconds:
            time.sleep(self._fake_load_seconds)
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def max_image_dimensions(self) -> tuple[int, int] | None:
        if self._max_width is None or self._max_height is None:
            return None
        return (self._max_width, self._max_height)

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
        # A deterministic color derived from the seed and description, so the same
        # seed reproduces the same bytes (FR-006) without anything resembling real
        # diffusion. Python's built-in hash() is salted per process, so a stable
        # digest is used instead.
        digest = hashlib.sha256(description.encode("utf-8")).digest()
        red = (seed or 0) % 256
        green = digest[0]
        blue = (steps or 0) % 256
        image = Image.new("RGB", (width, height), color=(red, green, blue))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        settings_used: dict[str, Any] = {
            "seed": seed,
            "steps": steps,
            "guidance": guidance,
            "width": width,
            "height": height,
        }
        return GeneratedImage(
            png_bytes=buffer.getvalue(),
            settings_used=settings_used,
            filter_note=self._filter_note,
        )
