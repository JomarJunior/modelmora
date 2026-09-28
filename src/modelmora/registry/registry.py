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
from modelmora.registry.digest import compute_digest
from modelmora.registry.store import ModelRecord, Slot, Store

__all__ = ["ModelRegistry", "ModelRecord", "RegisteredModel", "Slot"]


def _validate_local_path(label: str, path: str) -> None:
    """A record's `local_path` and every companion path must already exist on this
    Studio (T070, FR-026, FR-028): the registry cannot hold a hosted model or
    anything that runs off this machine, so a URL or a bare Hub identifier ("A URL"
    caught here directly; a Hub id such as "org/repo" is simply not an absolute path,
    caught by the check below it) is rejected before it is ever recorded, not
    discovered later as a load failure.
    """
    if "://" in path:
        raise ValueError(f"{label} must be a local file or directory, not a URL: {path!r}")
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be an absolute path on this Studio: {path!r}")
    if not candidate.exists():
        raise ValueError(f"{label} does not exist on this Studio: {path!r}")


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
        local_path: str | None = None,
        companion_paths: dict[str, str] | None = None,
        companion_digests: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> ModelRecord:
        """The real primitive behind `modelmora model add` (FR-020, FR-025).

        Opens a service period immediately: a record can be in service before it is
        complete (an incomplete record is simply never servable, T037), and retiring
        (`retire`) is the only thing that closes that period (FR-023). `local_path`
        and `companion_paths` (spec 002 amendment) are what let `serve` build a real
        runner from this record afterward (`cli.py`); a record added without one is
        listed and licence-tracked exactly as before, just never attached to a runner.
        Both, and every companion path, are validated as existing absolute paths on
        this Studio before anything is written (T070) -- never a URL or a Hub id.
        """
        if local_path is not None:
            _validate_local_path("local_path", local_path)
        for role, path in (companion_paths or {}).items():
            _validate_local_path(f"companion path {role!r}", path)

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
            local_path=local_path,
            companion_paths=companion_paths,
            companion_digests=companion_digests,
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

    def add_companion(self, name: str, version: str, *, role: str, path: str) -> ModelRecord:
        """Attaches a companion a runner needs to an existing record (T073, FR-020,
        FR-025) -- such as the `config` directory a single-file image checkpoint is
        loaded with -- digested now, so `serve`'s check before the first load covers
        it like any other companion (FR-022).

        Validated like every other path on a record (T070). A role already recorded is
        never replaced: that would silently change what "that exact version" means; a
        team member records a changed model as a new version instead.
        """
        _validate_local_path(f"companion path {role!r}", path)
        record = self._store.get_by_name_version(name, version)
        if record is None:
            raise ValueError(f"no model on record named {name!r} version {version!r}")
        if role in record.companion_paths:
            raise ValueError(
                f"{name} v{version} already records a {role!r} companion; "
                "record a changed model as a new version instead"
            )
        self._store.set_companion(record.id, role=role, path=path, digest=compute_digest(path))
        updated = self._store.get_by_id(record.id)
        assert updated is not None
        return updated

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

    def list_servable_records(self, kind: ModelKind | None = None) -> list[ModelRecord]:
        """Servable records with every field a real runner needs (`local_path`,
        `companion_paths`), unlike `list_servable`'s caller-facing `RegisteredModel`
        projection. `cli.py`'s `_run_serve` is the one caller (spec 002 amendment)."""
        return [
            r
            for r in self._store.list_models()
            if r.is_servable and (kind is None or r.kind == kind)
        ]

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
