"""Projects, notes, health, and diagnostics endpoints."""

from __future__ import annotations

import platform

from fastapi import APIRouter

from .. import __version__ as app_version
from ..core import paths
from ..core.config import get_config
from ..core.hardware import detect_hardware
from ..engine.manager import find_engine_binary, find_model_file, get_engine
from ..memory.store import MemoryStore
from ..ocr.engine import is_available as ocr_available
from .schemas import NoteCreate, ProjectCreate

router = APIRouter(prefix="/api", tags=["meta"])

_memory = MemoryStore()


@router.post("/projects")
def create_project(body: ProjectCreate):
    return {"project_id": _memory.create_project(body.name)}


@router.get("/projects")
def list_projects():
    return _memory.list_projects()


@router.post("/notes")
def create_note(body: NoteCreate):
    return {"note_id": _memory.add_note(body.content, body.project_id)}


@router.get("/notes")
def list_notes(project_id: str | None = None):
    return _memory.list_notes(project_id)


@router.get("/health")
def health():
    engine = get_engine()
    return {
        "status": "ok",
        "engine_running": engine.is_running(),
        "version": app_version,
    }


@router.get("/diagnostics")
def diagnostics():
    cfg = get_config()
    hw = detect_hardware()
    engine_binary = find_engine_binary()
    model_file = find_model_file(cfg.llm.model_file)
    engine = get_engine()

    return {
        "app": {"name": cfg.name, "version": app_version},
        "os": {"name": hw.os_name, "release": hw.os_release, "arch": hw.arch},
        "hardware": hw.as_dict(),
        "engine": {
            "binary_found": engine_binary is not None,
            "binary_path": str(engine_binary) if engine_binary else None,
            "running": engine.is_running(),
        },
        "model": {
            "configured_file": cfg.llm.model_file,
            "found": model_file is not None,
            "path": str(model_file) if model_file else None,
        },
        "ocr": {"available": ocr_available()},
        "rag_enabled": cfg.rag.enabled,
        "memory_enabled": cfg.memory.enabled,
        "security": {
            "allow_code_execution": cfg.security.allow_code_execution,
            "telemetry": cfg.security.telemetry,
            "bind_host": cfg.server.host,
            "loopback_only": cfg.server.host in ("127.0.0.1", "localhost", "::1") and not cfg.server.allow_remote,
        },
        "project_root": str(paths.PROJECT_ROOT),
        "python": platform.python_version(),
        "server": {"host": cfg.server.host, "port": cfg.server.port},
    }
