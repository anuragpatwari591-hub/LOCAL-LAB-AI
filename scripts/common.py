"""Shared helpers for the scripts/*_main.py entrypoints.

These modules must import cleanly with only the Python standard library,
because `diagnose` and the early phase of `prepare` need to run before any
third-party dependency has necessarily been installed.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path


def project_root() -> Path:
    env_root = os.environ.get("LOCAL_LAB_AI_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if p.exists():
            return p
    # scripts/common.py -> parents[1] is the project root
    return Path(__file__).resolve().parents[1]


def is_windows() -> bool:
    return platform.system() == "Windows"


def find_python(root: Path) -> str:
    """Prefer the local virtualenv `prepare` created (all dependencies
    already installed there, no internet/pip needed at `start` time); fall
    back to whichever Python is currently running this script (dev mode)."""
    venv_dir = root / "runtime" / "venv"
    bundled = venv_dir / ("Scripts/python.exe" if is_windows() else "bin/python3")
    if bundled.exists():
        return str(bundled)
    return sys.executable


def load_manifest(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {}


def save_manifest(root: Path, data: dict) -> None:
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def log(message: str) -> None:
    print(f"[LOCAL-LAB-AI] {message}", flush=True)


def sha256_of_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
