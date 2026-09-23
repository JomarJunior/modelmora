"""Reads the ModelMora contract from the hub checkout this component sits inside.

The hub (`miraveja-ecosystem`) is the single source of truth for the contract. This
component never vendors a copy: it reads
`specs/002-modelmora-inference/contracts/modelmora-v1.yaml` from the hub checkout that
contains this component at `components/modelmora/`, or from `MODELMORA_CONTRACT_PATH`
when that layout does not hold (mirrors `miraveja_studiolink.contract`).
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml

_RELATIVE_TO_COMPONENT_ROOT = Path(
    "../../specs/002-modelmora-inference/contracts/modelmora-v1.yaml"
)


class ContractNotFound(RuntimeError):
    """The ModelMora contract document could not be located."""


def _component_root() -> Path:
    # src/modelmora/contract.py -> src/modelmora -> src -> component root
    return Path(__file__).resolve().parents[2]


def contract_path() -> Path:
    """The path to `modelmora-v1.yaml`, honoring `MODELMORA_CONTRACT_PATH`."""
    override = os.environ.get("MODELMORA_CONTRACT_PATH")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = (_component_root() / _RELATIVE_TO_COMPONENT_ROOT).resolve()
    if not path.is_file():
        raise ContractNotFound(
            f"ModelMora contract not found at {path}. Check out this component at "
            "components/modelmora/ inside a miraveja-ecosystem hub checkout, "
            "or set MODELMORA_CONTRACT_PATH."
        )
    return path


@functools.lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    """The parsed OpenAPI document, cached for the process lifetime."""
    with contract_path().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def schema(name: str) -> dict[str, Any]:
    """The raw JSON Schema for `components.schemas.<name>` in the contract."""
    document = load_contract()
    try:
        return document["components"]["schemas"][name]
    except KeyError as exc:
        raise ContractNotFound(f"No schema named {name!r} in the ModelMora contract") from exc


def contract_version() -> str:
    """The contract's published version, e.g. "1.0.0"."""
    return load_contract()["info"]["version"]
