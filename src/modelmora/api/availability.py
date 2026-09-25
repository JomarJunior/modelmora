"""The `availability` path (T047, FR-029): starting, running or stopping, what can be
served, and the length of the line -- nothing about another caller's requests
(FR-017). `state.lifecycle` (T046) is the single source of truth for the state field;
this module only assembles the wire message around it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from modelmora.messages import Availability, Servable

if TYPE_CHECKING:
    from modelmora.api.state import AppState


def build_availability(state: AppState) -> Availability:
    queue_length = len(state.line) if state.line is not None else 0
    return Availability(
        state=state.lifecycle.state,
        queueLength=queue_length,
        servable=Servable(
            text=len(state.registry.list_servable("text")),
            image=len(state.registry.list_servable("image")),
        ),
    )
