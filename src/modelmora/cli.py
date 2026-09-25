"""The `modelmora` command.

`serve` runs the loopback service. `model add|list|retire|verify` and
`model set-default` (T041) let a team member change the registry without touching
code (FR-025): every one of them opens the same SQLite file `serve` reads from
(`Config.db_path`), so a model added here is what `serve` and `listModels` see next.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from dataclasses import replace

import uvicorn

from modelmora.api.app import AppState, assert_loopback_host, create_app
from modelmora.config import BIND_HOST, Config
from modelmora.messages import FilterDisclosure, ModelKind
from modelmora.refusals import ModelMoraRefusal
from modelmora.registry.registry import ModelRecord, ModelRegistry, RegisteredModel
from modelmora.registry.verify import compute_digest, verify_before_load
from modelmora.runners.standin import StandInTextRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modelmora")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the loopback service.")
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument(
        "--test-mode",
        action="store_true",
        help="Serve stand-in models with no GPU instead of loading real weights (FR-033).",
    )

    model = subparsers.add_parser("model", help="Manage the registry.")
    model_commands = model.add_subparsers(dest="model_command", required=True)

    add = model_commands.add_parser("add", help="Record a new model (FR-020).")
    add.add_argument("--name", required=True)
    add.add_argument("--version", required=True)
    add.add_argument("--kind", required=True, choices=["text", "image"])
    add.add_argument(
        "--reads-images",
        action="store_true",
        help="Text models only: this model can also read images (FR-003).",
    )
    add.add_argument("--source", required=True, help="Where the model came from.")
    add.add_argument(
        "--weights-path",
        required=True,
        help="A local file or directory of weights; its digest is what later loads "
        "are checked against (FR-022).",
    )
    add.add_argument("--license", dest="license_name", default=None)
    add.add_argument("--license-source", default=None, help="Where the licence terms were read.")
    add.add_argument(
        "--confirm-license",
        action="store_true",
        help="Confirms the licence is open-weight and allows public exhibition of "
        "outputs (FR-021). Without it, the model is recorded but never servable.",
    )
    add.add_argument(
        "--filter-disclosure",
        choices=["none", "disclosed", "undisclosable"],
        default="none",
        help="Whether this model's built-in content filter can be reported when it "
        "changes an output (FR-008). `undisclosable` is never servable.",
    )
    add.add_argument("--added-by", default=None, help="Defaults to the current OS user (FR-020).")

    list_cmd = model_commands.add_parser("list", help="List models (FR-024).")
    list_cmd.add_argument(
        "--all",
        action="store_true",
        help="Include retired and incomplete records, with their service dates (FR-023, SC-006).",
    )

    retire = model_commands.add_parser("retire", help="Retire a model (FR-023).")
    retire.add_argument("--name", required=True)
    retire.add_argument("--version", required=True)

    verify = model_commands.add_parser(
        "verify", help="Check a model's files against its recorded digest (FR-022)."
    )
    verify.add_argument("--name", required=True)
    verify.add_argument("--version", required=True)
    verify.add_argument("--weights-path", required=True)

    set_default = model_commands.add_parser(
        "set-default", help="Change the default model for a slot (FR-025)."
    )
    set_default.add_argument("--slot", required=True, choices=["text", "text_with_images", "image"])
    set_default.add_argument("--name", required=True)
    set_default.add_argument("--version", required=True)

    return parser


def _test_mode_registry() -> tuple[ModelRegistry, dict[tuple[str, str], StandInTextRunner]]:
    registry = ModelRegistry()  # in-memory: test mode never touches the Studio's file
    model = RegisteredModel(
        name="standin-text",
        version="1",
        kind="text",
        reads_images=False,
        license="N/A (test mode)",
    )
    registry.register(model, default_for=["text"])
    runners = {
        (model.name, model.version): StandInTextRunner(name=model.name, version=model.version)
    }
    return registry, runners


def _run_serve(args: argparse.Namespace) -> int:
    assert_loopback_host(BIND_HOST)
    config = Config.from_env()
    if args.port is not None:
        config = replace(config, port=args.port)

    if args.test_mode:
        registry, runners = _test_mode_registry()
    else:
        # No real runner exists yet (the diffusers/transformers loader is T023, GPU
        # only); models added with `modelmora model add` are already visible here and
        # to `listModels`, but nothing can be generated from them until that lands.
        registry, runners = ModelRegistry(config.db_path), {}

    state = AppState(config=config, registry=registry, runners=runners)  # type: ignore[arg-type]
    app = create_app(state)
    print(f"ModelMora listening on http://{BIND_HOST}:{config.port} (loopback only)")
    uvicorn.run(app, host=BIND_HOST, port=config.port, log_level="info")
    return 0


def _print_record(record: ModelRecord, *, show_service_dates: bool) -> None:
    status = "servable" if record.is_servable else "not servable"
    line = (
        f"{record.name}\tv{record.version}\t{record.kind}\t"
        f"license={record.license_name or '(none)'}\t{status}"
    )
    if show_service_dates:
        period = record.service_periods[-1] if record.service_periods else None
        ended = period.ended_at.isoformat() if period and period.ended_at else "in service"
        started = period.started_at.isoformat() if period else "?"
        line += f"\t{started} -> {ended}"
    print(line)


def _run_model_add(args: argparse.Namespace) -> int:
    registry = ModelRegistry(Config.from_env().db_path)
    added_by = args.added_by or getpass.getuser()
    kind: ModelKind = args.kind
    filter_disclosure: FilterDisclosure = args.filter_disclosure
    record = registry.add_model(
        name=args.name,
        version=args.version,
        kind=kind,
        reads_images=args.reads_images,
        source=args.source,
        weights_digest=compute_digest(args.weights_path),
        added_by=added_by,
        license_name=args.license_name,
        license_source=args.license_source,
        license_confirmed_by=added_by if args.confirm_license else None,
        filter_disclosure=filter_disclosure,
    )
    _print_record(record, show_service_dates=False)
    if not record.is_complete:
        print(
            "recorded but not yet servable: needs a licence name, a licence source "
            "and --confirm-license (FR-021)",
            file=sys.stderr,
        )
    return 0


def _run_model_list(args: argparse.Namespace) -> int:
    registry = ModelRegistry(Config.from_env().db_path)
    records = registry.list_all()
    if not args.all:
        records = [r for r in records if r.is_servable]
    for record in records:
        _print_record(record, show_service_dates=args.all)
    defaults = registry.defaults()
    for slot, model in defaults.items():
        if model is not None:
            print(f"default[{slot}] = {model.name} v{model.version}")
    return 0


def _run_model_retire(args: argparse.Namespace) -> int:
    registry = ModelRegistry(Config.from_env().db_path)
    try:
        record = registry.retire(args.name, args.version)
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 1
    _print_record(record, show_service_dates=True)
    return 0


def _run_model_verify(args: argparse.Namespace) -> int:
    registry = ModelRegistry(Config.from_env().db_path)
    record = registry.resolve_record(args.name, args.version)
    if record is None:
        print(f"no model on record named {args.name!r} version {args.version!r}", file=sys.stderr)
        return 1
    try:
        verify_before_load(record, args.weights_path)
    except ModelMoraRefusal as refusal:
        # verify_before_load already logged the WARNING line (plan.md "Telling the
        # team"); this is the CLI's own non-zero exit for the same event.
        print(refusal.detail, file=sys.stderr)
        return 1
    print(f"{record.name} v{record.version} files match the recorded digest")
    return 0


def _run_model_set_default(args: argparse.Namespace) -> int:
    registry = ModelRegistry(Config.from_env().db_path)
    try:
        registry.set_default(args.slot, args.name, args.version)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"default[{args.slot}] = {args.name} v{args.version}")
    return 0


_MODEL_COMMANDS = {
    "add": _run_model_add,
    "list": _run_model_list,
    "retire": _run_model_retire,
    "verify": _run_model_verify,
    "set-default": _run_model_set_default,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "model":
        return _MODEL_COMMANDS[args.model_command](args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
