"""The manual on-Studio check (T049/T061, quickstart Scenario 7).

Runs the real `modelmora serve` path (spec 002 amendment) as a subprocess and talks
to it over loopback HTTP, the same way a Studio component would: a text request and
an image request against the Studio's own registered collection (`.modelmora/`,
T060), a natural eviction decided by the real GPU's own capacity (no capacity reduced
by hand), availability across the lifecycle, and a clean shutdown on the same signal
an operator's Ctrl+C sends. Not part of CI: no GPU-free stand-in can prove real
residency or a real eviction, so this is run by hand on the Studio machine, with the
`gpu` extra installed and a `llama-server` binary available:

    uv run python -m modelmora.checks.studio_smoke

Only the standard library is imported here (mirroring `runners/llamacpp.py`), so
importing this module never needs the `gpu` extra; running it does.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CALLER_TOKEN = "studio-smoke-token"  # noqa: S105 -- a loopback-only test token, not a secret
CALLER_NAME = "studio-smoke"

# checks/ -> modelmora/ -> src/ -> the component repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _REPO_ROOT / ".modelmora" / "registry.sqlite3"

PORT = int(os.environ.get("MODELMORA_SMOKE_PORT", "8907"))
_BASE_URL = f"http://127.0.0.1:{PORT}"
_MAX_WAIT_SECONDS = 30  # the contract's own cap on a single long poll (R-6)

TEXT_MODEL_NAME = os.environ.get("MODELMORA_SMOKE_TEXT_MODEL_NAME", "the Studio's GGUF text model")
IMAGE_MODEL_NAME = os.environ.get("MODELMORA_SMOKE_IMAGE_MODEL_NAME", "the default image checkpoint")


def _log(message: str) -> None:
    print(f"[studio_smoke] {message}", flush=True)


def _gpu_memory_used_mib() -> str:
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return f"{result.stdout.strip()} MiB"
    except (OSError, subprocess.SubprocessError):
        return "unknown (nvidia-smi unavailable)"


def _request(
    method: str, path: str, *, json_body: dict[str, Any] | None = None, timeout: float = 10.0
) -> tuple[int, Any]:
    data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    request = urllib.request.Request(  # noqa: S310
        f"{_BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {CALLER_TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read()
        content_type = error.headers.get("Content-Type", "") if error.headers else ""
        status = error.code
    if "application/json" in content_type:
        return status, json.loads(body.decode("utf-8"))
    return status, body


def _poll_until_terminal(request_id: str, *, timeout_seconds: float) -> dict[str, Any]:
    """Repeats the 30-second long poll until a terminal state or `timeout_seconds`."""
    deadline = time.monotonic() + timeout_seconds
    body: Any = {}
    while time.monotonic() < deadline:
        status, body = _request(
            "GET",
            f"/modelmora/v1/requests/{request_id}",
            timeout=_MAX_WAIT_SECONDS + 10,
        )
        assert status == 200, body
        if body["state"] not in ("waiting", "running"):
            return body
    raise AssertionError(f"did not finish within {timeout_seconds}s: {body}")


def _wait_for_state(target_states: tuple[str, ...], *, timeout_seconds: float) -> str:
    deadline = time.monotonic() + timeout_seconds
    last = "unreachable"
    while time.monotonic() < deadline:
        try:
            status, body = _request("GET", "/modelmora/v1/availability", timeout=5.0)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.5)
            continue
        if status == 200:
            last = body["state"]
            if last in target_states:
                return last
        time.sleep(0.5)
    raise AssertionError(f"availability never reached {target_states}, last saw {last!r}")


def main() -> int:
    env = dict(os.environ)
    env.setdefault("MODELMORA_DB_PATH", str(_DEFAULT_DB_PATH))
    env.setdefault("MODELMORA_CALLER_TOKENS", f"{CALLER_TOKEN}:{CALLER_NAME}")
    env["MODELMORA_PORT"] = str(PORT)
    env.setdefault("MODELMORA_LLAMA_SERVER_BIN", "/data/llamacpp/bin/llama-b11191/llama-server")
    env.setdefault(
        "MODELMORA_LLAMA_CUDART_LIB_DIR",
        "/data/llamacpp/cudart/cudart-llama-b11191-bin-ubuntu-cuda-13.4-x64",
    )
    env.setdefault("HF_HOME", "/data/hf-cache")
    # T064: the exact local snapshot directory already cached under HF_HOME above --
    # `ImageRunner.load()` passes this straight to `from_single_file`'s own `config`
    # argument, bypassing repo-id/Hub cache resolution entirely, proven offline.
    env.setdefault(
        "MODELMORA_SDXL_CONFIG_PATH",
        "/data/hf-cache/hub/<base SDXL pipeline snapshot>/"
        "snapshots/462165984030d82259a11f4367a4eed129e94a7b",
    )
    env["HF_HUB_OFFLINE"] = "1"  # belt: this run must not touch the network at all

    if not Path(env["MODELMORA_DB_PATH"]).exists():
        raise AssertionError(
            f"no registry at {env['MODELMORA_DB_PATH']}; run `modelmora model add` for the "
            f"Studio's collection first (T060, docs/usage.md)"
        )

    _log(f"database: {env['MODELMORA_DB_PATH']}")
    _log(f"GPU memory before starting: {_gpu_memory_used_mib()}")
    _log(f"starting `modelmora serve` on port {PORT}...")
    process = subprocess.Popen([sys.executable, "-m", "modelmora.cli", "serve"], env=env)  # noqa: S603
    try:
        starting_state = _wait_for_state(("starting", "running"), timeout_seconds=30.0)
        _log(f"availability moments after start: {starting_state}")
        _wait_for_state(("running",), timeout_seconds=30.0)
        _, availability = _request("GET", "/modelmora/v1/availability")
        _log(f"availability once running: {availability}")
        assert availability["state"] == "running"
        assert availability["servable"]["text"] >= 1
        assert availability["servable"]["image"] >= 1

        _log(f"submitting a text request to {TEXT_MODEL_NAME}...")
        started = time.monotonic()
        status, submitted = _request(
            "POST",
            "/modelmora/v1/requests",
            json_body={
                "kind": "text",
                "instructions": "In one sentence, describe an empty gallery at dawn.",
            },
        )
        assert status == 202, submitted
        text_status = _poll_until_terminal(submitted["requestId"], timeout_seconds=180)
        _log(
            f"text result in {time.monotonic() - started:.1f}s "
            f"(GPU {_gpu_memory_used_mib()}): {text_status['result']['text']!r}"
        )
        assert text_status["state"] == "done"
        assert text_status["result"]["model"]["name"] == TEXT_MODEL_NAME

        _log(
            f"submitting an image request to {IMAGE_MODEL_NAME} -- the real GPU capacity "
            f"decides whether the text model must be evicted (FR-009), nothing forced by hand..."
        )
        started = time.monotonic()
        status, submitted = _request(
            "POST",
            "/modelmora/v1/requests",
            json_body={
                "kind": "image",
                "description": "A quiet museum gallery at dawn, soft light, no figures.",
                "size": {"width": 832, "height": 1216},
                "settings": {"seed": 7, "steps": 24},
            },
        )
        assert status == 202, submitted
        image_status = _poll_until_terminal(submitted["requestId"], timeout_seconds=240)
        _log(
            f"image result in {time.monotonic() - started:.1f}s "
            f"(GPU {_gpu_memory_used_mib()}), settingsUsed={image_status['result']['settingsUsed']}"
        )
        assert image_status["state"] == "done"

        status, image_bytes = _request(
            "GET", f"/modelmora/v1/requests/{submitted['requestId']}/image", timeout=30
        )
        assert status == 200
        _log(f"fetched {len(image_bytes)} bytes of PNG, never an error about memory")

        _log("asking the text model again -- proves it reloads correctly after any eviction...")
        started = time.monotonic()
        status, submitted = _request(
            "POST",
            "/modelmora/v1/requests",
            json_body={"kind": "text", "instructions": "One more sentence, about closing time."},
        )
        assert status == 202, submitted
        text_status_2 = _poll_until_terminal(submitted["requestId"], timeout_seconds=180)
        _log(
            f"second text result in {time.monotonic() - started:.1f}s: "
            f"{text_status_2['result']['text']!r}"
        )
        assert text_status_2["state"] == "done"

        _log("checking same-seed reproducibility (FR-006, T067)...")
        seeded_body = {
            "kind": "text",
            "instructions": "Write one sentence describing an empty gallery at dawn.",
            "settings": {"seed": 777, "temperature": 0.8},
        }
        status, first_seeded = _request("POST", "/modelmora/v1/requests", json_body=seeded_body)
        assert status == 202, first_seeded
        first_seeded_status = _poll_until_terminal(first_seeded["requestId"], timeout_seconds=180)
        status, second_seeded = _request("POST", "/modelmora/v1/requests", json_body=seeded_body)
        assert status == 202, second_seeded
        second_seeded_status = _poll_until_terminal(second_seeded["requestId"], timeout_seconds=180)
        first_text = first_seeded_status["result"]["text"]
        second_text = second_seeded_status["result"]["text"]
        _log(f"same seed, same request, twice: {first_text!r} == {second_text!r}")
        assert first_text == second_text, "same model, request and seed produced different text"

        _log("stopping `modelmora serve` (SIGINT, the same signal an operator's Ctrl+C sends)...")
        process.send_signal(signal.SIGINT)
        try:
            exit_code = process.wait(timeout=30.0)
        except subprocess.TimeoutExpired:
            process.kill()
            raise AssertionError("`modelmora serve` did not stop within 30s of SIGINT") from None
        _log(f"`modelmora serve` exited with code {exit_code} (GPU {_gpu_memory_used_mib()})")
        assert exit_code == 0, "a clean shutdown must not crash the process"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10.0)

    _log("all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
