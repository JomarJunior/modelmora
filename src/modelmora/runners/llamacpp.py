"""Real text (and, with a vision projector, image-reading text) generation for a
`.gguf` model, via a managed `llama-server` subprocess (spec 002 amendment, T058).

`transformers` cannot hold an architecture this large's full-precision graph, and the
Studio's collection ships it pre-quantized as GGUF; `llama.cpp`'s own server is the
established way to serve that format. This module only ever talks to that subprocess
over loopback HTTP with the standard library (`urllib`, `json`, `subprocess`) -- no
package this module imports is heavier than what CI already has, so nothing here
needs a lazy import to stay GPU-free (FR-033, FR-034). What *is* Studio-specific is
the `llama-server` binary and its CUDA runtime libraries, which do not ship with this
repository or any pip package; both are supplied by path (constructor arguments or
environment variables), never fetched here.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from modelmora.runners.base import GeneratedText, Runner

_HEALTH_TIMEOUT_SECONDS = 120.0
_HEALTH_POLL_SECONDS = 0.5
_DEFAULT_MAX_TOKENS = 512


class LlamaServerStartupError(RuntimeError):
    """Raised when the managed `llama-server` subprocess never became healthy."""


def _read_json(request: urllib.request.Request, *, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        return body


class LlamaCppTextRunner(Runner):
    """One `.gguf` model, served by its own `llama-server` process on loopback.

    Declares its footprint from the GGUF (and mmproj, if any) file sizes at
    construction, since that is known immediately, unlike a runner that only learns
    its real footprint once weights are actually resident (`runners/text.py`,
    `runners/image.py`); nothing here refines it further after `load()`, since
    `llama-server` does not expose the resident allocation over its API.
    """

    kind = "text"

    def __init__(
        self,
        *,
        name: str,
        version: str,
        model_path: str,
        mmproj_path: str | None = None,
        reads_images: bool = False,
        host: str = "127.0.0.1",
        port: int | None = None,
        n_gpu_layers: int = 999,
        context_size: int = 4096,
        server_binary: str | None = None,
        cudart_lib_dir: str | None = None,
        startup_timeout_seconds: float = _HEALTH_TIMEOUT_SECONDS,
    ) -> None:
        self.name = name
        self.version = version
        self.reads_images = reads_images and mmproj_path is not None
        self._model_path = model_path
        self._mmproj_path = mmproj_path
        self._host = host
        self._port = port or int(os.environ.get("MODELMORA_LLAMA_SERVER_PORT", "8901"))
        self._n_gpu_layers = n_gpu_layers
        self._context_size = context_size
        # No repository or pip package ships the llama.cpp binaries or their CUDA
        # runtime; both are Studio-machine configuration, supplied here or through
        # these two environment variables (see docs/usage.md).
        self._server_binary = server_binary or os.environ.get(
            "MODELMORA_LLAMA_SERVER_BIN", "llama-server"
        )
        self._cudart_lib_dir = cudart_lib_dir or os.environ.get("MODELMORA_LLAMA_CUDART_LIB_DIR")
        self._startup_timeout_seconds = startup_timeout_seconds
        self._process: subprocess.Popen[bytes] | None = None
        footprint = Path(model_path).stat().st_size if Path(model_path).exists() else 0
        if mmproj_path and Path(mmproj_path).exists():
            footprint += Path(mmproj_path).stat().st_size
        self._footprint_bytes = footprint

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def declared_footprint_bytes(self) -> int:
        return self._footprint_bytes

    def is_loaded(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def load(self) -> None:
        if self.is_loaded():
            return
        command = [
            self._server_binary,
            "-m",
            self._model_path,
            "-ngl",
            str(self._n_gpu_layers),
            "-c",
            str(self._context_size),
            "--host",
            self._host,
            "--port",
            str(self._port),
        ]
        if self._mmproj_path:
            command += ["--mmproj", self._mmproj_path]

        env = dict(os.environ)
        if self._cudart_lib_dir:
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = (
                f"{self._cudart_lib_dir}:{existing}" if existing else self._cudart_lib_dir
            )

        self._process = subprocess.Popen(  # noqa: S603
            command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._wait_until_healthy()

    def _wait_until_healthy(self) -> None:
        deadline = time.monotonic() + self._startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise LlamaServerStartupError(
                    f"{self.name} v{self.version}: llama-server exited during startup "
                    f"(code {self._process.returncode})"
                )
            try:
                request = urllib.request.Request(f"{self._base_url}/health")  # noqa: S310
                _read_json(request, timeout=2.0)
                return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(_HEALTH_POLL_SECONDS)
        self.unload()
        raise LlamaServerStartupError(
            f"{self.name} v{self.version}: llama-server did not become healthy within "
            f"{self._startup_timeout_seconds}s"
        )

    def unload(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=10.0)
        self._process = None

    def _chat_messages(
        self,
        *,
        instructions: str,
        conversation: list[dict[str, str]] | None,
        images: list[bytes] | None,
    ) -> list[dict[str, Any]]:
        role_for = {"caller": "user", "model": "assistant"}
        messages: list[dict[str, Any]] = [
            {"role": role_for[turn["speaker"]], "content": turn["text"]}
            for turn in conversation or []
        ]
        if images:
            import base64

            content: list[dict[str, Any]] = [{"type": "text", "text": instructions}]
            content += [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64.b64encode(b).decode()}"},
                }
                for b in images
            ]
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": instructions})
        return messages

    def generate_text(
        self,
        *,
        instructions: str,
        conversation: list[dict[str, str]] | None = None,
        images: list[bytes] | None = None,
        seed: int | None = None,
        max_length: int | None = None,
        temperature: float | None = None,
    ) -> GeneratedText:
        if images and not self.reads_images:
            raise ValueError(f"{self.name} cannot read images")
        if not self.is_loaded():
            raise RuntimeError(f"{self.name} v{self.version} is not loaded")

        payload: dict[str, Any] = {
            "messages": self._chat_messages(
                instructions=instructions, conversation=conversation, images=images
            ),
            "max_tokens": max_length or _DEFAULT_MAX_TOKENS,
        }
        if seed is not None:
            payload["seed"] = seed
        if temperature is not None:
            payload["temperature"] = temperature

        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(request, timeout=max(60.0, (max_length or _DEFAULT_MAX_TOKENS) * 0.5))
        message = body["choices"][0]["message"]
        # A model whose chat template preserves reasoning (this model family's does, by default)
        # can spend its whole token budget "thinking" and leave `content` empty; the
        # reasoning trace is still real generated text about the request, so it is
        # what is returned rather than nothing (spec Assumptions carry no promise
        # that a model's thinking is discarded, only that what is returned is honest
        # about being this model's output).
        text = message.get("content") or message.get("reasoning_content") or ""

        settings_used: dict[str, Any] = {
            "seed": seed,
            "maxLength": max_length,
            "temperature": temperature,
        }
        return GeneratedText(text=text, settings_used=settings_used, filter_note=None)
