"""The closed refusal reason set (FR-011) and the exception that carries it.

`ModelMoraRefusal.detail` is for the team, never for a caller's content: it must never
hold request or result content (FR-030). Callers raising it are responsible for that;
this module only carries the reason and detail through to the wire as a `Refusal`.
"""

from __future__ import annotations

from modelmora.messages import Refusal, RefusalReason

# Whether a reason carries retryAfterSeconds: the first three say "wait", the rest say
# "this will not work as asked" (data-model.md).
CARRIES_RETRY_AFTER: dict[RefusalReason, bool] = {
    "busy": True,
    "starting": True,
    "stopping": True,
    "unknown_model": False,
    "model_unavailable": False,
    "invalid_request": False,
    "cannot_be_served_on_this_studio": False,
    "failed_during_generation": False,
}

HTTP_STATUS: dict[RefusalReason, int] = {
    "busy": 409,
    "starting": 503,
    "stopping": 503,
    "unknown_model": 404,
    "model_unavailable": 404,
    "invalid_request": 400,
    "cannot_be_served_on_this_studio": 400,
    "failed_during_generation": 500,
}


class ModelMoraRefusal(Exception):
    """Raised anywhere a request must be refused or a run must fail.

    `detail` is a note for the team (naming a model, a limit, a mismatch); it must
    never contain a caller's instructions, description or generated content (FR-030).
    """

    def __init__(
        self,
        reason: RefusalReason,
        *,
        detail: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        if retry_after_seconds is not None and not CARRIES_RETRY_AFTER.get(reason, False):
            raise ValueError(f"{reason!r} does not carry retryAfterSeconds")
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail
        self.retry_after_seconds = retry_after_seconds

    @property
    def http_status(self) -> int:
        return HTTP_STATUS[self.reason]

    def to_message(self) -> Refusal:
        return Refusal(
            reason=self.reason,
            detail=self.detail,
            retryAfterSeconds=self.retry_after_seconds,
        )
