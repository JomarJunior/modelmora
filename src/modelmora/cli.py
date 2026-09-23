"""The `modelmora` command.

`serve` is enough for the MVP (Phases 1-3): `model add|list|retire|verify` and
`set-default` land with the SQLite registry in Phase 6 (T041).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

import uvicorn

from modelmora.api.app import AppState, assert_loopback_host, create_app
from modelmora.config import BIND_HOST, Config
from modelmora.registry.defaults import ModelRegistry, RegisteredModel
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
    return parser


def _test_mode_registry() -> tuple[ModelRegistry, dict[tuple[str, str], StandInTextRunner]]:
    registry = ModelRegistry()
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
        registry, runners = ModelRegistry(), {}
        print(
            "modelmora: no real models on record yet -- `modelmora model add` lands "
            "with the registry (roadmap 002 Phase 6). Pass --test-mode to serve "
            "stand-ins with no GPU.",
            file=sys.stderr,
        )

    state = AppState(config=config, registry=registry, runners=runners)  # type: ignore[arg-type]
    app = create_app(state)
    print(f"ModelMora listening on http://{BIND_HOST}:{config.port} (loopback only)")
    uvicorn.run(app, host=BIND_HOST, port=config.port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _run_serve(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
