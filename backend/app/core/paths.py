"""Portable path resolution.

LOCAL-LAB-AI must run from any drive letter or mount point (USB stick,
dev checkout, packaged distribution). Never hardcode absolute paths.

Resolution order for PROJECT_ROOT:
1. LOCAL_LAB_AI_ROOT environment variable, set by the start/prepare
   launcher scripts to the directory the launcher itself lives in.
2. Walk up from this file's location (backend/app/core/paths.py -> repo root).
"""

from __future__ import annotations

import os
from pathlib import Path


def _detect_project_root() -> Path:
    env_root = os.environ.get("LOCAL_LAB_AI_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if p.exists():
            return p

    # backend/app/core/paths.py -> parents[3] is the project root
    here = Path(__file__).resolve()
    return here.parents[3]


PROJECT_ROOT: Path = _detect_project_root()

BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG_DIR = PROJECT_ROOT / "config"
MODELS_DIR = PROJECT_ROOT / "models"
LLM_MODELS_DIR = MODELS_DIR / "llm"
OCR_MODELS_DIR = MODELS_DIR / "ocr"
EMBEDDINGS_MODELS_DIR = MODELS_DIR / "embeddings"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
ENGINE_DIR = RUNTIME_DIR / "engine"
BIN_DIR = RUNTIME_DIR / "bin"
DATA_DIR = PROJECT_ROOT / "data"
MEMORY_DIR = DATA_DIR / "memory"
UPLOADS_DIR = DATA_DIR / "uploads"
PROJECTS_DIR = DATA_DIR / "projects"
LOGS_DIR = PROJECT_ROOT / "logs"
MANIFEST_PATH = PROJECT_ROOT / "manifest.json"


def ensure_data_dirs() -> None:
    for d in (MEMORY_DIR, UPLOADS_DIR, PROJECTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
