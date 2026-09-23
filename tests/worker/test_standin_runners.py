"""Stand-in runners: deterministic output, fake footprint and fake load time (R-10)."""

from __future__ import annotations

import time

import pytest

from modelmora.runners.standin import StandInImageRunner, StandInTextRunner


def test_text_runner_honors_seed_deterministically() -> None:
    runner = StandInTextRunner(name="synthetic-text", version="1.0")
    runner.load()
    first = runner.generate_text(instructions="hello", seed=7, max_length=50)
    second = runner.generate_text(instructions="hello", seed=7, max_length=50)
    assert first.text == second.text


def test_text_runner_reports_fake_footprint() -> None:
    runner = StandInTextRunner(name="synthetic-text", version="1.0", fake_footprint_bytes=123456)
    assert runner.declared_footprint_bytes() == 123456


def test_text_runner_simulates_load_time() -> None:
    runner = StandInTextRunner(name="synthetic-text", version="1.0", fake_load_seconds=0.05)
    assert not runner.is_loaded()
    started = time.monotonic()
    runner.load()
    elapsed = time.monotonic() - started
    assert runner.is_loaded()
    assert elapsed >= 0.05


def test_text_runner_refuses_images_it_cannot_read() -> None:
    runner = StandInTextRunner(name="synthetic-text", version="1.0", reads_images=False)
    runner.load()
    with pytest.raises(ValueError):
        runner.generate_text(instructions="describe this", images=[b"not-really-a-png"])


def test_image_runner_reports_size_seed_and_footprint() -> None:
    runner = StandInImageRunner(name="synthetic-image", version="1.0", fake_footprint_bytes=999)
    runner.load()
    assert runner.declared_footprint_bytes() == 999
    generated = runner.generate_image(
        description="a synthetic test scene", width=128, height=64, seed=3
    )
    assert generated.settings_used["width"] == 128
    assert generated.settings_used["height"] == 64
    assert generated.png_bytes.startswith(b"\x89PNG")


def test_image_runner_honors_seed_deterministically() -> None:
    runner = StandInImageRunner(name="synthetic-image", version="1.0")
    runner.load()
    first = runner.generate_image(
        description="a synthetic test scene", width=64, height=64, seed=11
    )
    second = runner.generate_image(
        description="a synthetic test scene", width=64, height=64, seed=11
    )
    assert first.png_bytes == second.png_bytes


def test_unload_resets_loaded_state() -> None:
    runner = StandInTextRunner(name="synthetic-text", version="1.0")
    runner.load()
    assert runner.is_loaded()
    runner.unload()
    assert not runner.is_loaded()
