"""The SQLite data-access layer behind the registry (T038).

Only this module touches `sqlite3` directly. It maps rows to `ModelRecord` — a plain
read model of every field in data-model.md's `model` and `service_period` tables plus
that model's default-slot assignments — and leaves every rule about what is *servable*
to `registry.py`, which is the only other module that imports this one.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

from modelmora.messages import FilterDisclosure, ModelKind

Slot = str  # "text" | "text_with_images" | "image" (data-model.md)

_SCHEMA = resources.files("modelmora.registry").joinpath("schema.sql").read_text()


def _parse(timestamp: str | None) -> datetime | None:
    return datetime.fromisoformat(timestamp) if timestamp is not None else None


def _format(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


@dataclass(frozen=True)
class ServicePeriod:
    started_at: datetime
    ended_at: datetime | None


@dataclass(frozen=True)
class ModelRecord:
    """Every field data-model.md's `model` table names, plus its service history.

    A record is **complete** only with a licence name, a licence source and a
    confirmation (data-model.md); completeness and being in service are independent —
    retiring a model (FR-023) closes its service period without erasing the licence
    trail (SC-005).
    """

    id: int
    name: str
    version: str
    kind: ModelKind
    reads_images: bool
    license_name: str | None
    license_source: str | None
    source: str
    weights_digest: str
    added_by: str
    added_at: datetime
    license_confirmed_by: str | None
    license_confirmed_at: datetime | None
    filter_disclosure: FilterDisclosure
    service_periods: tuple[ServicePeriod, ...]

    @property
    def is_complete(self) -> bool:
        return bool(self.license_name and self.license_source and self.license_confirmed_by)

    @property
    def in_service(self) -> bool:
        return bool(self.service_periods) and self.service_periods[-1].ended_at is None

    @property
    def is_servable(self) -> bool:
        """FR-021 (complete, confirmed licence) and the filter-disclosure gate (T037a):
        an undisclosable built-in filter is never servable, whatever the licence says."""
        return self.is_complete and self.in_service and self.filter_disclosure != "undisclosable"


class Store:
    """One SQLite connection per registry, schema applied on first use.

    Shared across the request-handling and worker threads (`resolve` and
    `default_for_slot` are read from both), so the connection is opened with
    `check_same_thread=False` and every access is serialized by `_lock` -- registry
    reads and writes are rare enough next to generation itself that this is not a
    contended path.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._lock = threading.RLock()  # reentrant: get_default calls get_by_id
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def insert_model(
        self,
        *,
        name: str,
        version: str,
        kind: ModelKind,
        reads_images: bool,
        source: str,
        weights_digest: str,
        added_by: str,
        added_at: datetime,
        license_name: str | None,
        license_source: str | None,
        license_confirmed_by: str | None,
        license_confirmed_at: datetime | None,
        filter_disclosure: FilterDisclosure,
    ) -> int:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO model (
                    name, version, kind, reads_images, license_name, license_source,
                    source, weights_digest, added_by, added_at,
                    license_confirmed_by, license_confirmed_at, filter_disclosure
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    version,
                    kind,
                    int(reads_images),
                    license_name,
                    license_source,
                    source,
                    weights_digest,
                    added_by,
                    _format(added_at),
                    license_confirmed_by,
                    _format(license_confirmed_at) if license_confirmed_at else None,
                    filter_disclosure,
                ),
            )
            model_id = cursor.lastrowid
            assert model_id is not None
            self._connection.execute(
                "INSERT INTO service_period (model_id, started_at, ended_at) VALUES (?, ?, NULL)",
                (model_id, _format(added_at)),
            )
            self._connection.commit()
            return model_id

    def _row_to_record(self, row: sqlite3.Row, periods: list[sqlite3.Row]) -> ModelRecord:
        return ModelRecord(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            kind=row["kind"],
            reads_images=bool(row["reads_images"]),
            license_name=row["license_name"],
            license_source=row["license_source"],
            source=row["source"],
            weights_digest=row["weights_digest"],
            added_by=row["added_by"],
            added_at=_parse(row["added_at"]) or datetime.now(UTC),
            license_confirmed_by=row["license_confirmed_by"],
            license_confirmed_at=_parse(row["license_confirmed_at"]),
            filter_disclosure=row["filter_disclosure"],
            service_periods=tuple(
                ServicePeriod(
                    started_at=_parse(p["started_at"]) or datetime.now(UTC),
                    ended_at=_parse(p["ended_at"]),
                )
                for p in periods
            ),
        )

    def _fetch_periods(self, model_id: int) -> list[sqlite3.Row]:
        self._connection.row_factory = sqlite3.Row
        return list(
            self._connection.execute(
                "SELECT started_at, ended_at FROM service_period "
                "WHERE model_id = ? ORDER BY started_at",
                (model_id,),
            )
        )

    def get_by_name_version(self, name: str, version: str) -> ModelRecord | None:
        with self._lock:
            self._connection.row_factory = sqlite3.Row
            row = self._connection.execute(
                "SELECT * FROM model WHERE name = ? AND version = ?", (name, version)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row, self._fetch_periods(row["id"]))

    def get_by_id(self, model_id: int) -> ModelRecord | None:
        with self._lock:
            self._connection.row_factory = sqlite3.Row
            row = self._connection.execute(
                "SELECT * FROM model WHERE id = ?", (model_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row, self._fetch_periods(row["id"]))

    def list_models(self) -> list[ModelRecord]:
        with self._lock:
            self._connection.row_factory = sqlite3.Row
            rows = self._connection.execute("SELECT * FROM model ORDER BY added_at").fetchall()
            return [self._row_to_record(row, self._fetch_periods(row["id"])) for row in rows]

    def close_service_period(self, model_id: int, *, ended_at: datetime) -> None:
        with self._lock:
            self._connection.execute(
                """
                UPDATE service_period SET ended_at = ?
                WHERE model_id = ? AND ended_at IS NULL
                """,
                (_format(ended_at), model_id),
            )
            self._connection.commit()

    def set_default(self, slot: Slot, model_id: int) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO default_model (slot, model_id) VALUES (?, ?) "
                "ON CONFLICT (slot) DO UPDATE SET model_id = excluded.model_id",
                (slot, model_id),
            )
            self._connection.commit()

    def get_default(self, slot: Slot) -> ModelRecord | None:
        with self._lock:
            self._connection.row_factory = sqlite3.Row
            row = self._connection.execute(
                "SELECT model_id FROM default_model WHERE slot = ?", (slot,)
            ).fetchone()
            if row is None:
                return None
            return self.get_by_id(row["model_id"])
