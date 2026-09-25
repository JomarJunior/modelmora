"""Runtime configuration and its defaults (plan.md "Defaults").

Every default is pinned here rather than left to a caller or an environment variable
guess: line limit 32 (never below the SC-002 burst size of 20, so that criterion
measures results rather than `busy` refusals), bounded overtaking 2 minutes, result
holding 1 hour, idle-unload 10 minutes. The bind host is fixed to `127.0.0.1` (FR-027):
there is no field or environment variable that can change it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_LINE_LIMIT = 32
DEFAULT_OVERTAKING_SECONDS = 120
DEFAULT_HOLDING_SECONDS = 3600
DEFAULT_IDLE_UNLOAD_SECONDS = 600
DEFAULT_PORT = 8431
DEFAULT_DB_PATH = "modelmora.db"

# SC-002's burst is 20 requests; a lower line limit would make "busy" refusals the
# reason SC-002 passes rather than actual results, which defeats the criterion.
_MIN_LINE_LIMIT = 20

BIND_HOST = "127.0.0.1"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def _env_caller_tokens(name: str = "MODELMORA_CALLER_TOKENS") -> dict[str, str]:
    """Parses `token:caller,token:caller,...` into {token: caller name} (R-9)."""
    raw = os.environ.get(name)
    if not raw:
        return {}
    tokens: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        token, _, caller = pair.partition(":")
        if not token or not caller:
            raise ValueError(f"malformed entry in {name}: {pair!r}, want token:caller")
        tokens[token] = caller
    return tokens


@dataclass(frozen=True)
class Config:
    line_limit: int = DEFAULT_LINE_LIMIT
    overtaking_seconds: int = DEFAULT_OVERTAKING_SECONDS
    holding_seconds: int = DEFAULT_HOLDING_SECONDS
    idle_unload_seconds: int = DEFAULT_IDLE_UNLOAD_SECONDS
    port: int = DEFAULT_PORT
    # {bearer token: caller name}. An ownership marker, not a security boundary —
    # loopback is (R-9).
    caller_tokens: dict[str, str] = field(default_factory=dict)
    # The one SQLite file for the registry and the served-model history (plan.md
    # "Storage"). Never the store for request or result content (FR-030).
    db_path: str = DEFAULT_DB_PATH

    def __post_init__(self) -> None:
        if self.line_limit < _MIN_LINE_LIMIT:
            raise ValueError(
                f"line_limit must be at least {_MIN_LINE_LIMIT} (SC-002), got {self.line_limit}"
            )

    @property
    def host(self) -> str:
        return BIND_HOST

    def caller_for_token(self, token: str) -> str | None:
        return self.caller_tokens.get(token)

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            line_limit=_env_int("MODELMORA_LINE_LIMIT", DEFAULT_LINE_LIMIT),
            overtaking_seconds=_env_int("MODELMORA_OVERTAKING_SECONDS", DEFAULT_OVERTAKING_SECONDS),
            holding_seconds=_env_int("MODELMORA_HOLDING_SECONDS", DEFAULT_HOLDING_SECONDS),
            idle_unload_seconds=_env_int(
                "MODELMORA_IDLE_UNLOAD_SECONDS", DEFAULT_IDLE_UNLOAD_SECONDS
            ),
            port=_env_int("MODELMORA_PORT", DEFAULT_PORT),
            caller_tokens=_env_caller_tokens(),
            db_path=os.environ.get("MODELMORA_DB_PATH", DEFAULT_DB_PATH),
        )
