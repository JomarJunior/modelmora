"""Default-model resolution for the three slots: text, text_with_images, image.

This is a stub in front of the real SQLite registry (T038/T039): the same interface
(`register`, `resolve`, `default_for_slot`, `list_servable`) will be backed by the
database once it lands, so callers of this module (`api/validate.py`,
`api/requests.py`) never need to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from modelmora.messages import ModelKind

Slot = str  # "text" | "text_with_images" | "image" (data-model.md)


@dataclass(frozen=True)
class RegisteredModel:
    name: str
    version: str
    kind: ModelKind
    reads_images: bool
    license: str


class ModelRegistry:
    """In-memory servable models and their per-slot defaults."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], RegisteredModel] = {}
        self._defaults: dict[Slot, tuple[str, str]] = {}

    def register(self, model: RegisteredModel, *, default_for: list[Slot] | None = None) -> None:
        self._models[(model.name, model.version)] = model
        for slot in default_for or []:
            self._defaults[slot] = (model.name, model.version)

    def resolve(self, name: str, version: str) -> RegisteredModel | None:
        return self._models.get((name, version))

    def default_for_slot(self, slot: Slot) -> RegisteredModel | None:
        ref = self._defaults.get(slot)
        return self._models.get(ref) if ref else None

    def list_servable(self, kind: ModelKind | None = None) -> list[RegisteredModel]:
        return [m for m in self._models.values() if kind is None or m.kind == kind]

    def defaults(self) -> dict[Slot, RegisteredModel | None]:
        return {
            "text": self.default_for_slot("text"),
            "text_with_images": self.default_for_slot("text_with_images"),
            "image": self.default_for_slot("image"),
        }
