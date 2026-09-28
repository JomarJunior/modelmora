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

import ctypes
import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from modelmora.runners.base import GeneratedText, Runner

_HEALTH_TIMEOUT_SECONDS = 120.0
_HEALTH_POLL_SECONDS = 0.5
DEFAULT_MAX_TOKENS = 512

# Calibrated from the Studio (RTX 4090, spec 002 amendment log): the Studio's GGUF
# text model resident measured ~19.2GB total GPU against ~18.8GB of file sizes (main + mmproj) at
# context_size 4096 -- the remaining ~0.4GB is the KV cache and llama-server's own
# runtime overhead, which grows with the context window. A calibrated constant, not
# an architecture-derived one (Principle IX): T063, the same idea as
# `estimate_activation_overhead_bytes` in `runners/image.py`.
_OVERHEAD_BYTES_PER_CONTEXT_TOKEN = 400_000_000 / 4096

_PR_SET_PDEATHSIG = 1  # linux/prctl.h; Linux-only (this Studio's kernel), T069


# A server that really offloaded its model holds at least this share of the weights'
# size in GPU memory; a CPU fallback holds almost none (T074). Deliberately loose:
# the point is to tell "on the GPU" from "not on the GPU", not to measure the load.
_MIN_OFFLOADED_SHARE = 0.5


def _gpu_memory_used_by_pid(pid: int) -> int | None:
    """GPU memory held by process `pid`, in bytes: 0 if it holds none, `None` when no
    GPU can be asked at all (no `nvidia-smi`: CI, a machine without one), in which
    case the offload check cannot tell and does not block (T074)."""
    try:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    used_mib = 0
    for line in result.stdout.strip().splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 2 and fields[0] == str(pid) and fields[1].isdigit():
            used_mib += int(fields[1])
    return used_mib * 1024 * 1024


class LlamaServerStartupError(RuntimeError):
    """Raised when the managed `llama-server` subprocess never became healthy, or
    when it answers but is not serving the model this runner was built for."""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _die_with_parent() -> None:
    """Run in the child right after `fork()`, before `exec()` (T069): if this Python
    process is ever killed outright (SIGKILL, an unhandled crash) rather than
    reaching `unload()`'s own `terminate()`, the kernel sends `llama-server` SIGTERM
    too, instead of leaving it orphaned and still holding the GPU. Linux-only
    (`prctl`), matching this Studio's kernel; harmless best-effort elsewhere.
    """
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(_PR_SET_PDEATHSIG, signal.SIGTERM)
    except OSError:
        pass


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
        # T069: each runner gets its own free loopback port unless told otherwise --
        # an explicit constructor argument (tests) or `MODELMORA_LLAMA_SERVER_PORT`
        # (an operator pinning a single instance) both still win, in that order.
        if port is not None:
            self._port = port
        elif "MODELMORA_LLAMA_SERVER_PORT" in os.environ:
            self._port = int(os.environ["MODELMORA_LLAMA_SERVER_PORT"])
        else:
            self._port = _find_free_port()
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
        footprint += int(context_size * _OVERHEAD_BYTES_PER_CONTEXT_TOKEN)  # T063: KV cache
        self._footprint_bytes = footprint

    @property
    def port(self) -> int:
        return self._port

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def declared_footprint_bytes(self) -> int:
        return self._footprint_bytes

    def context_window_tokens(self) -> int | None:
        return self._context_size

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
            # T068: the Studio's GGUF model's chat template thinks by default, which can spend
            # the whole token budget "thinking" and leave `content` empty. Disabling
            # reasoning at the server level (confirmed against this exact build,
            # b11191) means `content` is always what is returned -- never a
            # reasoning trace standing in for an answer.
            "--reasoning",
            "off",
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
            command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=_die_with_parent,  # T069: dies if this process is ever killed
        )
        self._wait_until_healthy()
        self._verify_offloaded()

    def _verify_offloaded(self) -> None:
        """A `llama-server` that cannot find its CUDA runtime falls back to the CPU
        without an error: an order of magnitude slower, while residency counts GPU
        memory it does not hold (T074, FR-009). Once healthy (weights loaded), a
        server asked to offload must actually hold them on the GPU; otherwise the
        load fails with a reason the team can act on, and the server is stopped.
        """
        if self._n_gpu_layers == 0 or self._process is None:
            return  # deliberately CPU-only: nothing to check
        weights = self._weights_bytes()
        if weights == 0:
            return  # no weights on disk to compare against
        used = _gpu_memory_used_by_pid(self._process.pid)
        if used is None:
            return  # no GPU to ask: cannot tell, so do not block
        if used >= weights * _MIN_OFFLOADED_SHARE:
            return
        self.unload()
        raise LlamaServerStartupError(
            f"{self.name} v{self.version}: llama-server is not holding its model on the GPU "
            f"({used // (1024 * 1024)} MiB used for {weights // (1024 * 1024)} MiB of weights); "
            f"check that its CUDA runtime is found (MODELMORA_LLAMA_CUDART_LIB_DIR)"
        )

    def _weights_bytes(self) -> int:
        """The model file and its vision projector on disk: what offloading moves."""
        total = Path(self._model_path).stat().st_size if Path(self._model_path).exists() else 0
        if self._mmproj_path and Path(self._mmproj_path).exists():
            total += Path(self._mmproj_path).stat().st_size
        return total

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
                self._verify_serving_this_model()
                return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(_HEALTH_POLL_SECONDS)
        self.unload()
        raise LlamaServerStartupError(
            f"{self.name} v{self.version}: llama-server did not become healthy within "
            f"{self._startup_timeout_seconds}s"
        )

    def _verify_serving_this_model(self) -> None:
        """A stale `llama-server` already listening on this port would pass `/health`
        without ever being the model this runner was built for (T069). `/props`'s
        `model_path` is exactly the `-m` argument the intended server was started
        with, so an exact match is the whole check.
        """
        request = urllib.request.Request(f"{self._base_url}/props")  # noqa: S310
        body = _read_json(request, timeout=5.0)
        served_path = body.get("model_path")
        if served_path != self._model_path:
            raise LlamaServerStartupError(
                f"{self.name} v{self.version}: llama-server on port {self._port} is "
                f"serving {served_path!r}, not {self._model_path!r} -- a stale server "
                f"may already be listening on this port"
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
            "max_tokens": max_length or DEFAULT_MAX_TOKENS,
        }
        if seed is not None:
            payload["seed"] = seed
            # T067: llama-server's prompt cache (default on) can reuse a previous
            # request's cached computation for a shared prefix; measured on the
            # Studio to be reproducible even so for this model and build, but a
            # caller asking for a specific seed (FR-006) is asking to reproduce a
            # result exactly, and reusing another request's cached state is exactly
            # the kind of cross-request coupling that promise must not depend on.
            payload["cache_prompt"] = False
        if temperature is not None:
            payload["temperature"] = temperature

        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(request, timeout=max(60.0, (max_length or DEFAULT_MAX_TOKENS) * 0.5))
        message = body["choices"][0]["message"]
        # T068: reasoning is disabled server-side (`load()`'s `--reasoning off`), so
        # `content` is always the answer, never a reasoning trace standing in for
        # one. If a model still produced nothing -- an empty turn, not an error the
        # server itself raised -- that is a generation failure with a reason the
        # caller can act on (spec Edge Cases), not a silent empty result.
        text = message.get("content") or ""
        if not text:
            raise RuntimeError(f"{self.name} v{self.version} produced no answer")

        settings_used: dict[str, Any] = {
            "seed": seed,
            "maxLength": max_length,
            "temperature": temperature,
        }
        return GeneratedText(text=text, settings_used=settings_used, filter_note=None)
