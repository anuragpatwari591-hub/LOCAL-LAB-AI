"""llama.cpp process manager.

Launches the bundled `llama-server` binary (from runtime/bin/, placed there
by `prepare`) against a local GGUF model (from models/llm/), bound strictly
to loopback, and proxies chat requests to it. The engine is a private
implementation detail: nothing outside this process ever talks to it
directly, and it is never exposed on a non-loopback interface.
"""

from __future__ import annotations

import json
import platform
import socket
import subprocess
import time
from pathlib import Path
from typing import AsyncIterator

import httpx

from ..core import paths
from ..core.config import LLMConfig

_ENGINE_BINARY_NAMES = {
    "Windows": "llama-server.exe",
    "Linux": "llama-server",
    "Darwin": "llama-server",
}


class EngineNotReadyError(RuntimeError):
    pass


def find_engine_binary() -> Path | None:
    name = _ENGINE_BINARY_NAMES.get(platform.system(), "llama-server")
    for candidate_dir in (paths.BIN_DIR, paths.ENGINE_DIR):
        candidate = candidate_dir / name
        if candidate.exists():
            return candidate
    return None


def find_model_file(model_filename: str) -> Path | None:
    candidate = paths.LLM_MODELS_DIR / model_filename
    if candidate.exists():
        return candidate
    # Fall back to any single .gguf file present (useful in dev/test setups).
    ggufs = sorted(paths.LLM_MODELS_DIR.glob("*.gguf"))
    return ggufs[0] if len(ggufs) == 1 else None


def _pick_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


class LlamaEngine:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._process: subprocess.Popen | None = None
        self._port: int | None = None

    @property
    def base_url(self) -> str:
        if self._port is None:
            raise EngineNotReadyError("Engine has not been started yet.")
        return f"http://127.0.0.1:{self._port}"

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        if self.is_running():
            return

        binary = find_engine_binary()
        if binary is None:
            raise EngineNotReadyError(
                "Inference engine binary not found in runtime/bin or runtime/engine. "
                "Run `prepare` first to install the local llama.cpp engine."
            )

        model = find_model_file(self.config.model_file)
        if model is None:
            raise EngineNotReadyError(
                f"Model file '{self.config.model_file}' not found in models/llm/. "
                "Run `prepare` first to download the local model."
            )

        self._port = _pick_free_port(self.config.engine_port)

        cmd = [
            str(binary),
            "--model", str(model),
            "--host", "127.0.0.1",
            "--port", str(self._port),
            "--ctx-size", str(self.config.context_size),
            "--threads", str(self.config.threads),
            "--batch-size", str(self.config.batch_size),
            "--n-gpu-layers", "0",
            "--cache-type-k", self.config.kv_cache_type,
            "--cache-type-v", self.config.kv_cache_type,
            "--log-disable",
        ]

        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = open(paths.LOGS_DIR / "engine.log", "a", encoding="utf-8")
        self._process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(paths.PROJECT_ROOT),
        )

    def wait_until_healthy(self, timeout_s: float = 60.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if not self.is_running():
                return False
            try:
                resp = httpx.get(f"{self.base_url}/health", timeout=2.0)
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        return False

    def stop(self) -> None:
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    async def chat_completion_stream(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        if not self.is_running():
            raise EngineNotReadyError("Engine is not running.")

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/v1/chat/completions", json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def complete_raw(self, prompt: str, max_tokens: int, temperature: float = 0.4) -> str:
        """Plain-text completion via llama.cpp's native /completion endpoint.

        Unlike chat_completion, this never applies a chat template, so it
        works even against a model/tokenizer that has no (or an incomplete)
        chat template - e.g. the tiny structural test fixture used in
        tests/integration/test_engine_real_inference.py. Not used by the
        product's chat UI, but kept as a lower-level building block.
        """
        if not self.is_running():
            raise EngineNotReadyError("Engine is not running.")

        payload = {"prompt": prompt, "n_predict": max_tokens, "temperature": temperature}
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(f"{self.base_url}/completion", json=payload)
            resp.raise_for_status()
            return resp.json().get("content", "")

    async def chat_completion(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        if not self.is_running():
            raise EngineNotReadyError("Engine is not running.")

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


_engine_singleton: LlamaEngine | None = None


def get_engine(config: LLMConfig | None = None) -> LlamaEngine:
    global _engine_singleton
    if _engine_singleton is None:
        from ..core.config import get_config

        _engine_singleton = LlamaEngine(config or get_config().llm)
    return _engine_singleton
