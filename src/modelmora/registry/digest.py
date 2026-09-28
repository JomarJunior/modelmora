"""Content digests over model weight and companion files.

Split out of `registry/verify.py` so `registry/store.py` can compute a digest during
its own migration (T062, backfilling `companion_digests` for a record that predates
that column) without an import cycle: `verify.py` needs `ModelRecord` from
`store.py`, so `store.py` cannot import `verify.py` back.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Streamed, not read whole: the Studio's own models run into tens of gigabytes each
# (spec 002 amendment); `read_bytes()` would try to hold one entirely in memory at once.
_CHUNK_BYTES = 8 * 1024 * 1024


def _update_with_file(digest: hashlib._Hash, file_path: Path) -> None:
    with file_path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)


def compute_digest(weights_path: str | Path) -> str:
    """A stable digest over one file or every file under a directory.

    Small synthetic files stand in for real weights in tests (FR-033): this hashes
    whatever is there, real weights or a tiny fixture, the same way.
    """
    path = Path(weights_path)
    digest = hashlib.sha256()
    if path.is_file():
        _update_with_file(digest, path)
    else:
        for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(file_path.relative_to(path)).encode("utf-8"))
            _update_with_file(digest, file_path)
    return f"sha256:{digest.hexdigest()}"
