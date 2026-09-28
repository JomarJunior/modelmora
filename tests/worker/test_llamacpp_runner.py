"""`LlamaCppTextRunner` behavior that does not need a real `llama-server` process
(T065, T067, T068, T069): everything here is proven by monkeypatching the two points
this module touches the outside world through -- `subprocess.Popen` and its own
`_read_json` -- never a real subprocess or socket.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from modelmora.runners import llamacpp
from modelmora.runners.llamacpp import LlamaCppTextRunner, LlamaServerStartupError


def _runner(**overrides: object) -> LlamaCppTextRunner:
    base: dict[str, object] = dict(
        name="synthetic-gguf-model",
        version="1.0",
        model_path="/tmp/does-not-matter.gguf",
    )
    base.update(overrides)
    return LlamaCppTextRunner(**base)  # type: ignore[arg-type]


def test_two_runners_with_no_port_given_get_different_free_ports() -> None:
    """T069: each runner its own free loopback port, not a fixed shared one."""
    first = _runner()
    second = _runner(name="synthetic-gguf-model-two")

    assert first.port != second.port
    assert first.port > 0 and second.port > 0


def test_an_explicit_port_is_still_honored() -> None:
    runner = _runner(port=54321)
    assert runner.port == 54321


def test_the_env_var_still_pins_a_port_when_no_explicit_one_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODELMORA_LLAMA_SERVER_PORT", "54322")
    runner = _runner()
    assert runner.port == 54322


def test_context_window_tokens_reports_the_configured_context_size() -> None:
    runner = _runner(context_size=8192)
    assert runner.context_window_tokens() == 8192


def test_footprint_includes_kv_cache_overhead_for_the_context_size() -> None:
    """T063: not just the (here, nonexistent) file sizes on disk."""
    runner = _runner(context_size=4096)
    assert runner.declared_footprint_bytes() > 0


def test_load_starts_llama_server_with_reasoning_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """T068: disabled at the server level, not left to a per-request workaround."""
    captured: dict[str, Any] = {}

    class _FakeProcess:
        def poll(self) -> int | None:
            return None

    def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        captured["command"] = command
        captured["preexec_fn"] = kwargs.get("preexec_fn")
        return _FakeProcess()

    monkeypatch.setattr(llamacpp.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(LlamaCppTextRunner, "_wait_until_healthy", lambda self: None)

    runner = _runner()
    runner.load()

    assert "--reasoning" in captured["command"]
    assert captured["command"][captured["command"].index("--reasoning") + 1] == "off"
    assert captured["preexec_fn"] is llamacpp._die_with_parent


def test_a_seeded_request_disables_the_prompt_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """T067: cache_prompt is off whenever a seed is given, never left to the default."""
    captured: dict[str, Any] = {}

    def fake_read_json(request: object, *, timeout: float) -> dict[str, Any]:
        body = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
        captured["payload"] = body
        return {"choices": [{"message": {"content": "a generated sentence"}}]}

    monkeypatch.setattr(llamacpp, "_read_json", fake_read_json)
    runner = _runner()
    runner._process = _AlwaysAlive()  # type: ignore[assignment]

    runner.generate_text(instructions="say something", seed=7)

    assert captured["payload"]["seed"] == 7
    assert captured["payload"]["cache_prompt"] is False


def test_an_unseeded_request_leaves_the_prompt_cache_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_read_json(request: object, *, timeout: float) -> dict[str, Any]:
        captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
        return {"choices": [{"message": {"content": "a generated sentence"}}]}

    monkeypatch.setattr(llamacpp, "_read_json", fake_read_json)
    runner = _runner()
    runner._process = _AlwaysAlive()  # type: ignore[assignment]

    runner.generate_text(instructions="say something")

    assert "cache_prompt" not in captured["payload"]


def test_an_empty_answer_fails_rather_than_returning_a_reasoning_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T068: no `content`, whatever `reasoning_content` might hold, is a failure."""

    def fake_read_json(request: object, *, timeout: float) -> dict[str, Any]:
        return {
            "choices": [
                {"message": {"content": "", "reasoning_content": "a hidden reasoning trace"}}
            ]
        }

    monkeypatch.setattr(llamacpp, "_read_json", fake_read_json)
    runner = _runner()
    runner._process = _AlwaysAlive()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="produced no answer"):
        runner.generate_text(instructions="say something")


def test_a_stale_server_on_the_port_fails_the_identity_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T069: `/health` alone is not enough to declare a runner ready."""

    def fake_read_json(request: object, *, timeout: float) -> dict[str, Any]:
        url = request.full_url  # type: ignore[attr-defined]
        if url.endswith("/health"):
            return {"status": "ok"}
        return {"model_path": "/some/other/model.gguf"}

    monkeypatch.setattr(llamacpp, "_read_json", fake_read_json)
    runner = _runner(model_path="/expected/model.gguf")

    with pytest.raises(LlamaServerStartupError, match="is serving"):
        runner._verify_serving_this_model()


def test_the_intended_server_passes_the_identity_check(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_json(request: object, *, timeout: float) -> dict[str, Any]:
        return {"model_path": "/expected/model.gguf"}

    monkeypatch.setattr(llamacpp, "_read_json", fake_read_json)
    runner = _runner(model_path="/expected/model.gguf")

    runner._verify_serving_this_model()  # raises nothing


class _AlwaysAlive:
    def poll(self) -> int | None:
        return None
