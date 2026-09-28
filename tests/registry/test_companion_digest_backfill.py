"""A database written before T062 gains `companion_digests`, backfilled from
whatever companion files are on disk today, without losing a record or its licence
trail (T062, matching T054's migration pattern for `local_path`/`companion_paths`).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from modelmora.registry.digest import compute_digest
from modelmora.registry.store import Store


def _write_pre_t062_database(path: Path, *, companion_path: str) -> None:
    """T054's schema: `local_path`/`companion_paths` exist, `companion_digests` does
    not yet."""
    connection = sqlite3.connect(str(path))
    connection.executescript(
        """
        CREATE TABLE model (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('text', 'image')),
            reads_images INTEGER NOT NULL DEFAULT 0 CHECK (reads_images IN (0, 1)),
            license_name TEXT,
            license_source TEXT,
            source TEXT NOT NULL,
            weights_digest TEXT NOT NULL,
            added_by TEXT NOT NULL,
            added_at TEXT NOT NULL,
            license_confirmed_by TEXT,
            license_confirmed_at TEXT,
            filter_disclosure TEXT NOT NULL DEFAULT 'none'
                CHECK (filter_disclosure IN ('none', 'disclosed', 'undisclosable')),
            local_path TEXT,
            companion_paths TEXT NOT NULL DEFAULT '{}',
            UNIQUE (name, version)
        );
        CREATE TABLE service_period (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL REFERENCES model (id),
            started_at TEXT NOT NULL,
            ended_at TEXT
        );
        CREATE TABLE default_model (
            slot TEXT PRIMARY KEY CHECK (slot IN ('text', 'text_with_images', 'image')),
            model_id INTEGER NOT NULL REFERENCES model (id)
        );
        """
    )
    connection.execute(
        """
        INSERT INTO model (
            name, version, kind, reads_images, license_name, license_source,
            source, weights_digest, added_by, added_at,
            license_confirmed_by, license_confirmed_at, filter_disclosure,
            local_path, companion_paths
        ) VALUES (
            'pre-t062-model', '1.0', 'text', 1, 'Synthetic-Open-License',
            'https://example.invalid/license', 'local fixture', 'sha256:pre-t062',
            'pre-t062-team-member', '2026-01-01T00:00:00+00:00',
            'pre-t062-team-member', '2026-01-01T00:00:00+00:00', 'none',
            '/tmp/pre-t062-weights.bin', ?
        )
        """,
        (json.dumps({"mmproj": companion_path}),),
    )
    connection.execute(
        "INSERT INTO service_period (model_id, started_at, ended_at) "
        "VALUES (1, '2026-01-01T00:00:00+00:00', NULL)"
    )
    connection.commit()
    connection.close()


def test_a_companion_digest_is_backfilled_from_the_file_already_on_disk(tmp_path: Path) -> None:
    mmproj = tmp_path / "mmproj.bin"
    mmproj.write_bytes(b"synthetic companion bytes already on disk")
    db_path = tmp_path / "pre-t062.sqlite3"
    _write_pre_t062_database(db_path, companion_path=str(mmproj))

    store = Store(db_path)

    record = store.get_by_name_version("pre-t062-model", "1.0")
    assert record is not None
    assert record.companion_digests == {"mmproj": compute_digest(mmproj)}
    # Nothing about the record's own identity or licence trail was disturbed.
    assert record.license_name == "Synthetic-Open-License"
    assert record.in_service


def test_a_missing_companion_file_is_left_unbackfilled_rather_than_raising(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pre-t062-missing.sqlite3"
    _write_pre_t062_database(db_path, companion_path=str(tmp_path / "never-written.bin"))

    store = Store(db_path)  # must not raise

    record = store.get_by_name_version("pre-t062-model", "1.0")
    assert record is not None
    assert record.companion_digests == {}


def test_reopening_after_backfill_does_not_recompute(tmp_path: Path) -> None:
    mmproj = tmp_path / "mmproj.bin"
    mmproj.write_bytes(b"synthetic companion bytes")
    db_path = tmp_path / "pre-t062-idempotent.sqlite3"
    _write_pre_t062_database(db_path, companion_path=str(mmproj))
    Store(db_path).close()  # first open: backfills

    original_digest = compute_digest(mmproj)
    mmproj.write_bytes(b"a different file entirely, after the digest was recorded")

    store = Store(db_path)  # second open must not re-hash the (now different) file

    record = store.get_by_name_version("pre-t062-model", "1.0")
    assert record is not None
    assert record.companion_digests == {"mmproj": original_digest}
