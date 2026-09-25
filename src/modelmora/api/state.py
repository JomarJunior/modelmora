"""Everything the loopback service needs to answer a request (T030-T032).

Kept separate from `api/app.py` and `api/requests.py` so neither has to import the
other just to see this shape: `create_app` (`api/app.py`) builds the queue and starts
the worker exactly once, wiring it to the callbacks in `api/requests.py`; the request
handlers there take this state to enqueue work and to answer status and withdraw
calls. `line` and `worker` default to `None` and are filled in by `create_app`, not by
`__post_init__`, because the worker's callbacks close over `api/requests.py` functions
that must not be imported here (that would be the cycle this split avoids).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from modelmora.api.requests import RequestStore
from modelmora.config import Config
from modelmora.queue.estimates import Estimator
from modelmora.queue.line import Line
from modelmora.registry.registry import ModelRegistry
from modelmora.runners.base import Runner
from modelmora.worker.holding import ImageHoldingStore
from modelmora.worker.residency import Residency

if TYPE_CHECKING:
    from modelmora.worker.worker import Worker


@dataclass
class AppState:
    config: Config
    registry: ModelRegistry
    runners: dict[tuple[str, str], Runner] = field(default_factory=dict)
    store: RequestStore = field(default_factory=RequestStore)
    residency: Residency = field(default_factory=Residency)
    holding: ImageHoldingStore = field(default_factory=ImageHoldingStore)
    estimator: Estimator = field(default_factory=Estimator)
    line: Line | None = None
    worker: Worker | None = None

    def __post_init__(self) -> None:
        if self.line is None:
            self.line = Line(limit=self.config.line_limit)
