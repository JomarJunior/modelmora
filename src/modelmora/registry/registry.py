"""The registry (T039): SQLite-backed, replacing the in-memory stub `registry.defaults`
carried through Phases 1-5.

`ModelRegistry` keeps the exact interface that stub declared it would keep --
`register`, `resolve`, `default_for_slot`, `list_servable`, `defaults` -- so its
existing callers (`api/validate.py`, `api/app.py`, `api/requests.py`, `cli.py`, and
every fixture in `tests/conftest.py` and `tests/queue/conftest.py`) needed only an
import-path change, not a rewrite. `register()` remains the quick, already-confirmed
path those callers and test fixtures use; `add_model()` is the real primitive (FR-020)
behind `modelmora model add`, which can also record an incomplete or undisclosable
model on purpose, for the licence and filter-disclosure gates (T037, T037a) to refuse.

Interpretation carried here: a caller naming an incomplete, retired or
filter-undisclosable model gets `unknown_model`, the same refusal as a name that was
never on record at all. FR-011's reasons are what a caller may act on, and a caller has
no way to act differently on "not on record" versus "on record but unusable" --
telling them apart would leak registry internals no wire message carries (FR-017's
spirit: nothing beyond what a caller needs). `model_unavailable` is kept for the two
cases the spec names explicitly: a resolvable, servable model with no runner attached,
and a digest mismatch at load time (FR-022, T040).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from modelmora.messages import FilterDisclosure, ModelKind
from modelmora.registry.store import ModelRecord, Slot, Store

__all__ = ["ModelRegistry", "ModelRecord", "RegisteredModel", "Slot"]

_TEST_FIXTURE_PROVENANCE = {
    "source": "test-fixture",
    "weights_digest": "sha256:test-fixture",
    "added_by": "test-fixture",
    "license_source": "test-fixture",
    "license_confirmed_by": "test-fixture",
}


@dataclass(frozen=True)
class RegisteredModel:
    """The servable projection of a `ModelRecord`: what a caller-facing lookup needs.

    Kept as its own type, rather than exposing `ModelRecord` on the serving path, so
    `api/validate.py` and `api/app.py` never see fields (added_by, digest, service
    history) that have nothing to do with resolving or listing a model to serve.
    """

    name: str
    version: str
    kind: ModelKind
    reads_images: bool
    license: str


def _as_registered(record: ModelRecord) -> RegisteredModel:
    return RegisteredModel(
        name=record.name,
        version=record.version,
        kind=record.kind,
        reads_images=record.reads_images,
        license=record.license_name or "",
    )


class ModelRegistry:
    """SQLite-backed registry of models (data-model.md "Durable: the registry")."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._store = Store(path)

    def add_model(
        self,
        *,
        name: str,
        version: str,
        kind: ModelKind,
        source: str,
        weights_digest: str,
        added_by: str,
        reads_images: bool = False,
        license_name: str | None = None,
        license_source: str | None = None,
        license_confirmed_by: str | None = None,
        filter_disclosure: FilterDisclosure = "none",
        now: datetime | None = None,
    ) -> ModelRecord:
        """The real primitive behind `modelmora model add` (FR-020, FR-025).

        Opens a service period immediately: a record can be in service before it is
        complete (an incomplete record is simply never servable, T037), and retiring
        (`retire`) is the only thing that closes that period (FR-023).
        """
        moment = now or datetime.now(UTC)
        model_id = self._store.insert_model(
            name=name,
            version=version,
            kind=kind,
            reads_images=reads_images,
            source=source,
            weights_digest=weights_digest,
            added_by=added_by,
            added_at=moment,
            license_name=license_name,
            license_source=license_source,
            license_confirmed_by=license_confirmed_by,
            license_confirmed_at=moment if license_confirmed_by else None,
            filter_disclosure=filter_disclosure,
        )
        record = self._store.get_by_id(model_id)
        assert record is not None
        return record

    def register(self, model: RegisteredModel, *, default_for: list[Slot] | None = None) -> None:
        """Registers an already-confirmed, in-service record in one call.

        Used by test fixtures and `cli.py --test-mode`, which only ever describe a
        model by its servable projection; provenance fields FR-020 requires but these
        callers don't have an opinion on are filled with a marked fixture value, never
        used for anything but populating a required, non-null column.
        """
        self.add_model(
            name=model.name,
            version=model.version,
            kind=model.kind,
            reads_images=model.reads_images,
            license_name=model.license,
            filter_disclosure="none",
            **_TEST_FIXTURE_PROVENANCE,  # type: ignore[arg-type]
        )
        for slot in default_for or []:
            self.set_default(slot, model.name, model.version)

    def resolve(self, name: str, version: str) -> RegisteredModel | None:
        record = self._store.get_by_name_version(name, version)
        if record is None or not record.is_servable:
            return None
        return _as_registered(record)

    def resolve_record(self, name: str, version: str) -> ModelRecord | None:
        """The full record, servable or not -- for the CLI and the licence trail."""
        return self._store.get_by_name_version(name, version)

    def default_for_slot(self, slot: Slot) -> RegisteredModel | None:
        record = self._store.get_default(slot)
        if record is None or not record.is_servable:
            return None
        return _as_registered(record)

    def list_servable(self, kind: ModelKind | None = None) -> list[RegisteredModel]:
        return [
            _as_registered(r)
            for r in self._store.list_models()
            if r.is_servable and (kind is None or r.kind == kind)
        ]

    def list_all(self, kind: ModelKind | None = None) -> list[ModelRecord]:
        """Every record ever added, retired included (FR-023, SC-006)."""
        return [r for r in self._store.list_models() if kind is None or r.kind == kind]

    def defaults(self) -> dict[Slot, RegisteredModel | None]:
        return {
            "text": self.default_for_slot("text"),
            "text_with_images": self.default_for_slot("text_with_images"),
            "image": self.default_for_slot("image"),
        }

    def set_default(self, slot: Slot, name: str, version: str) -> None:
        record = self._store.get_by_name_version(name, version)
        if record is None or not record.is_servable:
            raise ValueError(
                f"{name!r} v{version!r} is not a complete, in-service record and "
                f"cannot be the default for {slot!r}"
            )
        self._store.set_default(slot, record.id)

    def retire(self, name: str, version: str, *, now: datetime | None = None) -> ModelRecord:
        """Closes the service period; the record and its licence stay forever (FR-023)."""
        record = self._store.get_by_name_version(name, version)
        if record is None:
            raise KeyError(f"no model on record named {name!r} version {version!r}")
        self._store.close_service_period(record.id, ended_at=now or datetime.now(UTC))
        retired = self._store.get_by_id(record.id)
        assert retired is not None
        return retired
