"""A model's own built-in filter is disclosed, never judged (FR-008, spec Edge Cases)."""

from __future__ import annotations

from modelmora.messages import ModelRef
from modelmora.runners.standin import StandInTextRunner
from modelmora.worker.results import text_result


def test_filter_note_is_carried_through_untouched() -> None:
    runner = StandInTextRunner(
        name="synthetic-filtered-model",
        version="1.0",
        filter_note="the model's built-in filter blanked part of this output",
    )
    runner.load()
    generated = runner.generate_text(instructions="say something", seed=1)

    result = text_result(
        model=ModelRef(name=runner.name, version=runner.version),
        generated=generated,
        holding_seconds=3600,
    )

    assert result.filterNote == "the model's built-in filter blanked part of this output"
    # ModelMora carries the model's own note through untouched; it adds no judgment
    # of its own (FR-008).
    assert result.text == generated.text


def test_no_filter_note_when_the_model_reports_none() -> None:
    runner = StandInTextRunner(name="synthetic-unfiltered-model", version="1.0")
    runner.load()
    generated = runner.generate_text(instructions="say something", seed=1)

    result = text_result(
        model=ModelRef(name=runner.name, version=runner.version),
        generated=generated,
        holding_seconds=3600,
    )

    assert result.filterNote is None
