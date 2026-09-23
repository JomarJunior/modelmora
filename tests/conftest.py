"""Shared fixtures: an AppState with two synthetic stand-in text models."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from modelmora.api.app import AppState, create_app
from modelmora.api.requests import RequestStore
from modelmora.config import Config
from modelmora.registry.defaults import ModelRegistry, RegisteredModel
from modelmora.runners.base import Runner
from modelmora.runners.standin import StandInTextRunner

CALLER_TOKEN = "sonavida-test-token"
CALLER_NAME = "sonavida"
OTHER_TOKEN = "curagusta-test-token"
OTHER_NAME = "curagusta"

TEXT_MODEL = RegisteredModel(
    name="synthetic-text-small",
    version="1.0",
    kind="text",
    reads_images=False,
    license="Synthetic-Test-License",
)
VISION_MODEL = RegisteredModel(
    name="synthetic-text-vision",
    version="1.0",
    kind="text",
    reads_images=True,
    license="Synthetic-Test-License",
)


def build_state() -> AppState:
    registry = ModelRegistry()
    registry.register(TEXT_MODEL, default_for=["text"])
    registry.register(VISION_MODEL, default_for=["text_with_images"])
    runners: dict[tuple[str, str], Runner] = {
        (TEXT_MODEL.name, TEXT_MODEL.version): StandInTextRunner(
            name=TEXT_MODEL.name, version=TEXT_MODEL.version, reads_images=False
        ),
        (VISION_MODEL.name, VISION_MODEL.version): StandInTextRunner(
            name=VISION_MODEL.name, version=VISION_MODEL.version, reads_images=True
        ),
    }
    config = Config(caller_tokens={CALLER_TOKEN: CALLER_NAME, OTHER_TOKEN: OTHER_NAME})
    return AppState(config=config, registry=registry, runners=runners, store=RequestStore())


@pytest.fixture
def state() -> AppState:
    return build_state()


@pytest.fixture
def client(state: AppState) -> TestClient:
    app = create_app(state)
    return TestClient(app, headers={"Authorization": f"Bearer {CALLER_TOKEN}"})
