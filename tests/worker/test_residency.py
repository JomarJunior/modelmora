"""GPU residency and eviction (T024, FR-009).

Every footprint here is declared by a stand-in, which is the point: eviction is the part
of the GPU story that must be provable with no GPU (R-10, FR-034).
"""

from __future__ import annotations

import pytest

from modelmora.runners.standin import StandInImageRunner, StandInTextRunner
from modelmora.worker.residency import CannotFit, Residency

ONE_GIB = 1024**3


def _text(name: str, footprint: int = ONE_GIB) -> StandInTextRunner:
    return StandInTextRunner(
        name=name, version="1.0", reads_images=False, fake_footprint_bytes=footprint
    )


def test_a_model_is_loaded_on_first_use() -> None:
    residency = Residency(capacity_bytes=4 * ONE_GIB)
    runner = _text("first")

    residency.ensure_loaded(runner)

    assert runner.is_loaded()
    assert residency.resident_runners() == [runner]


def test_models_share_the_gpu_while_they_fit() -> None:
    residency = Residency(capacity_bytes=4 * ONE_GIB)
    one, two = _text("one"), _text("two")

    residency.ensure_loaded(one)
    residency.ensure_loaded(two)

    assert one.is_loaded() and two.is_loaded()


def test_the_least_recently_used_model_is_evicted_to_make_room() -> None:
    """Two fit, the third does not: the oldest use goes."""
    residency = Residency(capacity_bytes=2 * ONE_GIB)
    first, second, third = _text("first"), _text("second"), _text("third")

    residency.ensure_loaded(first)
    residency.ensure_loaded(second)
    residency.touch(second)  # second is now the more recently used of the two

    residency.ensure_loaded(third)

    assert not first.is_loaded(), "the least recently used model was not evicted"
    assert second.is_loaded()
    assert third.is_loaded()


def test_an_image_model_evicts_a_text_model_when_it_needs_the_whole_gpu() -> None:
    """US2 acceptance scenario 2, at the residency level."""
    residency = Residency(capacity_bytes=2 * ONE_GIB)
    text = _text("text-model")
    image = StandInImageRunner(name="image-model", version="1.0", fake_footprint_bytes=2 * ONE_GIB)

    residency.ensure_loaded(text)
    residency.ensure_loaded(image)

    assert image.is_loaded()
    assert not text.is_loaded()


def test_a_model_that_cannot_fit_alone_is_rejected_rather_than_thrashing() -> None:
    """Refused, never queued forever (spec Edge Cases). The API refuses this earlier."""
    residency = Residency(capacity_bytes=ONE_GIB)
    too_big = _text("too-big", footprint=8 * ONE_GIB)

    assert not residency.fits_alone(too_big.declared_footprint_bytes())
    with pytest.raises(CannotFit):
        residency.ensure_loaded(too_big)
    assert not too_big.is_loaded()


def test_a_resident_model_is_not_loaded_twice() -> None:
    """A second ask for a resident model must not pay its load time again."""
    residency = Residency(capacity_bytes=4 * ONE_GIB)
    runner = _text("already-here")
    loads = 0
    original_load = runner.load

    def counting_load() -> None:
        nonlocal loads
        loads += 1
        original_load()

    runner.load = counting_load  # type: ignore[method-assign]

    residency.ensure_loaded(runner)
    residency.ensure_loaded(runner)

    assert loads == 1
    assert residency.resident_runners() == [runner]


def test_an_idle_model_is_unloaded_to_leave_the_gpu_free() -> None:
    """The idle-unload timeout keeps the GPU free between studio hours (config default 10 min)."""
    residency = Residency(capacity_bytes=4 * ONE_GIB)
    runner = _text("idle")
    residency.ensure_loaded(runner)

    unloaded = residency.unload_idle(idle_seconds=0)

    assert unloaded == [runner]
    assert not runner.is_loaded()
    assert residency.resident_runners() == []


def test_a_busy_model_is_left_alone_by_idle_unload() -> None:
    residency = Residency(capacity_bytes=4 * ONE_GIB)
    runner = _text("busy")
    residency.ensure_loaded(runner)

    unloaded = residency.unload_idle(idle_seconds=3600)

    assert unloaded == []
    assert runner.is_loaded()
