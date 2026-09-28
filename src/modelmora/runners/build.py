"""Building a real runner from a registry record (spec 002 amendment, T057).

Chooses the runner by kind and file format: a `.gguf` text model is served through
`LlamaCppTextRunner` (`runners/llamacpp.py`); anything else text is `TextRunner`
(`runners/text.py`, `transformers`); every image model goes through `ImageRunner`
(`runners/image.py`), which itself picks `from_single_file` or `from_pretrained` by
whether `local_path` names a file or a directory. A record with no `local_path`
(added before this amendment, or through the quick `register()` test-fixture path)
has no runner built for it: `serve` lists it and its licence, same as always, but a
caller asking for it gets `model_unavailable`, never a crash (`api/validate.py`).

None of the imports here are heavy: `runners/text.py`, `runners/image.py` and
`runners/llamacpp.py` each defer their own GPU-only imports into their methods, so
building this mapping, and thus `cli.py serve`, stays GPU-free to import (FR-033)
even though calling `load()` on what it returns is not.
"""

from __future__ import annotations

from pathlib import Path

from modelmora.registry.store import ModelRecord
from modelmora.runners.base import Runner
from modelmora.runners.image import ImageRunner
from modelmora.runners.llamacpp import LlamaCppTextRunner
from modelmora.runners.text import TextRunner


def declared_footprint_hint(path: Path) -> int:
    """A cheap, upfront size estimate for eviction (FR-009) before anything loads.

    A file's size on disk; a directory's is the sum of every file under it. A real
    `transformers`/`diffusers` runner overwrites this with a measured figure once it
    is actually resident (`runners/text.py`, `runners/image.py`) -- this is only ever
    the *first* estimate, needed so a request can be evicted for or refused
    `cannot_be_served_on_this_studio` correctly even before a model has ever loaded
    (`api/validate.py`, spec Edge Cases).
    """
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def build_runner(record: ModelRecord) -> Runner | None:
    """A real runner for `record`, or `None` if it has no `local_path` recorded yet."""
    if record.local_path is None:
        return None
    path = Path(record.local_path)

    if record.kind == "text":
        if path.suffix == ".gguf":
            return LlamaCppTextRunner(
                name=record.name,
                version=record.version,
                model_path=str(path),
                mmproj_path=record.companion_paths.get("mmproj"),
                reads_images=record.reads_images,
            )
        return TextRunner(
            name=record.name,
            version=record.version,
            model_path=str(path),
            reads_images=record.reads_images,
            declared_footprint_bytes=declared_footprint_hint(path),
        )

    return ImageRunner(
        name=record.name,
        version=record.version,
        model_path=str(path),
        declared_footprint_bytes=declared_footprint_hint(path),
        # T073: a single-file checkpoint's pipeline config and tokenizer, recorded as
        # the `config` companion, so `serve` loads it offline from the registry alone.
        sdxl_config_path=record.companion_paths.get("config"),
    )
