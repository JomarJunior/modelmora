"""The runner interface every model backend implements: text, image, or a stand-in.

A single interface (rather than one per kind) is what lets the worker (Phase 5) treat
every resident model the same way for loading, unloading and eviction, regardless of
what it generates. A runner only needs to override the `generate_*` method that
matches its own `kind`; the other raises `NotImplementedError` by default.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

from modelmora.messages import ModelKind


@dataclass
class GeneratedText:
    text: str
    settings_used: dict[str, Any]
    filter_note: str | None = None


@dataclass
class GeneratedImage:
    png_bytes: bytes
    settings_used: dict[str, Any]
    filter_note: str | None = None


class Runner(abc.ABC):
    """One servable model: its identity, residency lifecycle, and generation."""

    name: str
    version: str
    kind: ModelKind
    reads_images: bool = False

    @abc.abstractmethod
    def declared_footprint_bytes(self) -> int:
        """Memory the model needs while resident, real or faked (FR-009, R-10)."""

    @abc.abstractmethod
    def load(self) -> None:
        """Bring the model onto the GPU. Idempotent if already loaded."""

    @abc.abstractmethod
    def unload(self) -> None:
        """Free the model's memory. Idempotent if already unloaded."""

    @abc.abstractmethod
    def is_loaded(self) -> bool: ...

    def max_image_dimensions(self) -> tuple[int, int] | None:
        """Largest (width, height) this model can produce, or `None` if unconstrained.

        Checked before queueing (FR-011, US2 acceptance scenario 3): a size beyond this
        is refused as `invalid_request`, distinct from `cannot_be_served_on_this_studio`
        (declared footprint versus GPU capacity, checked separately).
        """
        return None

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
        raise NotImplementedError(f"{self.name} does not generate text")

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
        raise NotImplementedError(f"{self.name} does not generate images")
