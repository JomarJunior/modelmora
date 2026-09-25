"""A database written before the spec 002 amendment gains `local_path` and
`companion_paths` without losing a single record or its licence trail (T054).

`CREATE TABLE IF NOT EXISTS` in `schema.sql` no-ops once `model` already exists, so
without an explicit migration an old registry file would never gain these columns;
this is what proves `Store._ensure_local_path_columns` actually runs it.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from modelmora.registry.store import Store

_PRE_AMENDMENT_SCHEMA = """
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


def _write_pre_amendment_database(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    connection.executescript(_PRE_AMENDMENT_SCHEMA)
    connection.execute(
        """
        INSERT INTO model (
            name, version, kind, reads_images, license_name, license_source,
            source, weights_digest, added_by, added_at,
            license_confirmed_by, license_confirmed_at, filter_disclosure
        ) VALUES (
            'pre-amendment-model', '1.0', 'text', 0, 'Synthetic-Open-License',
            'https://example.invalid/license', 'local fixture', 'sha256:pre-amendment',
            'pre-amendment-team-member', '2026-01-01T00:00:00+00:00',
            'pre-amendment-team-member', '2026-01-01T00:00:00+00:00', 'none'
        )
        """
    )
    connection.execute(
        "INSERT INTO service_period (model_id, started_at, ended_at) "
        "VALUES (1, '2026-01-01T00:00:00+00:00', NULL)"
    )
    connection.commit()
    connection.close()


def test_an_old_database_gains_the_new_columns_without_losing_data(tmp_path: Path) -> None:
    db_path = tmp_path / "pre-amendment.sqlite3"
    _write_pre_amendment_database(db_path)

    store = Store(db_path)

    record = store.get_by_name_version("pre-amendment-model", "1.0")
    assert record is not None
    assert record.license_name == "Synthetic-Open-License"
    assert record.added_by == "pre-amendment-team-member"
    assert record.is_complete
    assert record.in_service
    # The columns this amendment adds exist and are usable, even though this record
    # predates them: `None` and `{}` are honest defaults, not lost data.
    assert record.local_path is None
    assert record.companion_paths == {}


def test_reopening_an_already_migrated_database_is_a_no_op(tmp_path: Path) -> None:
    db_path = tmp_path / "already-migrated.sqlite3"
    Store(db_path).close()  # created fresh, so already has the new columns

    store = Store(db_path)  # migration check must not fail or duplicate columns
    store.insert_model(
        name="synthetic-second-open",
        version="1.0",
        kind="image",
        reads_images=False,
        source="local fixture",
        weights_digest="sha256:second",
        added_by="team-member",
        added_at=datetime.now(UTC),
        license_name=None,
        license_source=None,
        license_confirmed_by=None,
        license_confirmed_at=None,
        filter_disclosure="none",
        local_path="/data/models/checkpoints/synthetic.safetensors",
        companion_paths={"vae": "/data/models/vae/synthetic-vae.safetensors"},
    )
    record = store.get_by_name_version("synthetic-second-open", "1.0")
    assert record is not None
    assert record.local_path == "/data/models/checkpoints/synthetic.safetensors"
    assert record.companion_paths == {"vae": "/data/models/vae/synthetic-vae.safetensors"}
