"""Configuration loading: config/default.yaml overridden by config/local.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from . import paths


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_raw() -> dict[str, Any]:
    default_path = paths.CONFIG_DIR / "default.yaml"
    local_path = paths.CONFIG_DIR / "local.yaml"

    with open(default_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            local_data = yaml.safe_load(f) or {}
        data = _deep_merge(data, local_data)

    return data


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    open_browser: bool = True
    allow_remote: bool = False


@dataclass
class LLMConfig:
    model_file: str = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    context_size: int = 2048
    threads: int = 2
    batch_size: int = 256
    gpu_layers: int = 0
    kv_cache_type: str = "q8_0"
    max_tokens: int = 512
    temperature: float = 0.4
    engine_port: int = 8712


@dataclass
class OCRConfig:
    enabled: bool = True
    language: str = "en"
    max_image_dim: int = 1600


@dataclass
class RAGConfig:
    enabled: bool = True
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    embedding_dim: int = 256


@dataclass
class MemoryConfig:
    enabled: bool = True
    max_history_messages: int = 20


@dataclass
class SecurityConfig:
    allow_code_execution: bool = False
    telemetry: bool = False


@dataclass
class AppConfig:
    name: str = "LOCAL-LAB-AI"
    version: str = "1.0.0"
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    default_mode: str = "general"


def _build_config(raw: dict[str, Any]) -> AppConfig:
    app = raw.get("app", {})
    return AppConfig(
        name=app.get("name", "LOCAL-LAB-AI"),
        version=app.get("version", "1.0.0"),
        server=ServerConfig(**raw.get("server", {})),
        llm=LLMConfig(**raw.get("llm", {})),
        ocr=OCRConfig(**raw.get("ocr", {})),
        rag=RAGConfig(**raw.get("rag", {})),
        memory=MemoryConfig(**raw.get("memory", {})),
        security=SecurityConfig(**raw.get("security", {})),
        default_mode=raw.get("modes", {}).get("default", "general"),
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return _build_config(_load_raw())


def reload_config() -> AppConfig:
    get_config.cache_clear()
    return get_config()
