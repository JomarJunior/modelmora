"""Assembling a wire `Result` from a runner's generated output.

Every result carries the model name and version that produced it (SC-005) and the
settings actually used, not what was hoped for (FR-002, FR-008); `filterNote` is
carried through untouched whenever a model's own built-in filter changed its output.
**🧠 ModelMora** adds no judgment of its own here (FR-008).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from modelmora.messages import ModelRef, Result
from modelmora.runners.base import GeneratedImage, GeneratedText


def text_result(*, model: ModelRef, generated: GeneratedText, holding_seconds: int) -> Result:
    return Result(
        model=model,
        text=generated.text,
        imageAvailable=False,
        settingsUsed=generated.settings_used,
        filterNote=generated.filter_note,
        heldUntil=datetime.now(UTC) + timedelta(seconds=holding_seconds),
    )


def image_result(*, model: ModelRef, generated: GeneratedImage, holding_seconds: int) -> Result:
    return Result(
        model=model,
        text=None,
        imageAvailable=True,
        settingsUsed=generated.settings_used,
        filterNote=generated.filter_note,
        heldUntil=datetime.now(UTC) + timedelta(seconds=holding_seconds),
    )
