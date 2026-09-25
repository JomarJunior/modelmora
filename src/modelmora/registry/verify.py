"""The file digest check (FR-022, R-8, T040).

A model's recorded `weights_digest` is the way to confirm the files on the Studio are
that exact version. `compute_digest` is used twice: once when a model is added (the
digest recorded then is what every later load is checked against), and again by
`modelmora model verify` and by whatever loads the files (the real runner, T023,
outside this phase's scope -- it must call `verify_before_load` before its first
`load()`, the seam this module leaves for it).

"Telling the team" (plan.md) is one channel everywhere: a `WARNING` line in the
operator log naming the model, version and expected digest. The caller never sees the
digest; it only ever sees `model_unavailable`.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.store import ModelRecord

logger = logging.getLogger("modelmora.registry")


def compute_digest(weights_path: str | Path) -> str:
    """A stable digest over one file or every file under a directory.

    Small synthetic files stand in for real weights in tests (FR-033): this hashes
    whatever is there, real weights or a tiny fixture, the same way.
    """
    path = Path(weights_path)
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    else:
        for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(file_path.relative_to(path)).encode("utf-8"))
            digest.update(file_path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def verify_before_load(record: ModelRecord, weights_path: str | Path) -> None:
    """Refuses `model_unavailable` and tells the team on a version mismatch (FR-022).

    Called before a model's first load. Stand-in runners never call this -- they carry
    no files to check -- so it only fires once a real runner (T023) is wired to it.
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
