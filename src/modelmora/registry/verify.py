"""The file digest check (FR-022, R-8, T040), and verifying a whole record before its
first real load in `serve` (T062).

`compute_digest` (`registry/digest.py`, re-exported here for every existing caller)
is used three times: once when a model is added (the digest recorded then is what
every later load is checked against), again by `modelmora model verify`, and again by
`VerifyingRunner` -- the wrapper `cli.py`'s `_run_serve` puts around every real runner
it builds, so a model's files are checked before its very first load in `serve` itself,
not only through the separate `model verify` command. Hashing a Studio-sized checkpoint
(7-18GB) takes real seconds, so `VerifyingRunner` does this exactly once per process,
lazily, on the first `load()` call -- never on every load/unload/reload cycle an idle
timeout or an eviction might cause.

"Telling the team" (plan.md) is one channel everywhere: a `WARNING` line in the
operator log naming the model, version and expected digest. The caller never sees the
digest; it only ever sees `model_unavailable`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.digest import compute_digest
from modelmora.registry.store import ModelRecord
from modelmora.runners.base import GeneratedImage, GeneratedText, Runner

__all__ = [
    "VerifyingRunner",
    "compute_digest",
    "verify_before_load",
    "verify_companions_before_load",
    "verify_record_before_load",
]

logger = logging.getLogger("modelmora.registry")


def verify_before_load(record: ModelRecord, weights_path: str | Path) -> None:
    """Refuses `model_unavailable` and tells the team on a version mismatch (FR-022).

    Checks `weights_path` against `record.weights_digest` -- the main weights only,
    the same check this has always been (`modelmora model verify` still calls this
    with whatever `--weights-path` the operator names). `verify_record_before_load`
    below is the wider check `serve` itself needs: the record's own recorded
    `local_path`, plus every companion file.
    """
    actual = compute_digest(weights_path)
    if actual != record.weights_digest:
        logger.warning(
            "model files do not match the recorded version: %s v%s expected digest %s",
            record.name,
            record.version,
            record.weights_digest,
        )
        raise ModelMoraRefusal(
            "model_unavailable",
            detail=f"{record.name} v{record.version} files do not match the recorded version",
        )


def verify_companions_before_load(record: ModelRecord) -> None:
    """Checks every companion file whose digest was recorded (T054, T062).

    A companion added before this task existed has no recorded digest yet
    (`registry/store.py`'s migration backfills one from whatever is on disk today,
    the moment it can); until then there is nothing to compare against, so that
    companion is silently not checked here rather than refused for a digest that was
    simply never computed.
    """
    for role, path in sorted(record.companion_paths.items()):
        expected = record.companion_digests.get(role)
        if expected is None:
            continue
        actual = compute_digest(path)
        if actual != expected:
            logger.warning(
                "model companion file does not match the recorded version: "
                "%s v%s companion %r expected digest %s",
                record.name,
                record.version,
                role,
                expected,
            )
            raise ModelMoraRefusal(
                "model_unavailable",
                detail=(
                    f"{record.name} v{record.version} companion file {role!r} "
                    f"does not match the recorded version"
                ),
            )


def verify_record_before_load(record: ModelRecord) -> None:
    """Everything `serve` needs checked before a record's very first real load (T062):
    its own `local_path` against `weights_digest`, and every companion file."""
    if record.local_path is not None:
        verify_before_load(record, record.local_path)
    verify_companions_before_load(record)


class VerifyingRunner(Runner):
    """Wraps a real runner (T057's `build_runner` output) so `verify_record_before_load`
    runs before that runner's very first `load()` -- the seam `build_runner` itself
    deliberately leaves closed (its own tests, T056, assert it returns the bare
    `TextRunner`/`ImageRunner`/`LlamaCppTextRunner`); `cli.py`'s `_run_serve` is where
    this wrapping happens, so every other caller of `build_runner` is unaffected.
    """

    def __init__(self, inner: Runner, record: ModelRecord) -> None:
        self._inner = inner
        self._record = record
        self._verified = False
        self.name = inner.name
        self.version = inner.version
        self.kind = inner.kind
        self.reads_images = inner.reads_images

    def declared_footprint_bytes(self) -> int:
        return self._inner.declared_footprint_bytes()

    def footprint_bytes_for_image(self, *, width: int, height: int) -> int:
        return self._inner.footprint_bytes_for_image(width=width, height=height)

    def context_window_tokens(self) -> int | None:
        return self._inner.context_window_tokens()

    def is_loaded(self) -> bool:
        return self._inner.is_loaded()

    def max_image_dimensions(self) -> tuple[int, int] | None:
        return self._inner.max_image_dimensions()

    def load(self) -> None:
        if not self._verified:
            verify_record_before_load(self._record)
            self._verified = True
        self._inner.load()

    def unload(self) -> None:
        self._inner.unload()

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
        return self._inner.generate_text(
            instructions=instructions,
            conversation=conversation,
            images=images,
            seed=seed,
            max_length=max_length,
            temperature=temperature,
        )

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
        return self._inner.generate_image(
            description=description,
            avoid=avoid,
            width=width,
            height=height,
            seed=seed,
            steps=steps,
            guidance=guidance,
        )
