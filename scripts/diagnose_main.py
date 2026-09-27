#!/usr/bin/env python3
"""Diagnostic report: OS, hardware, and which local assets are present.

Deliberately stdlib-only (plus psutil if available) so it works even if
`prepare` was never run and nothing has been pip-installed yet.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import is_windows, load_manifest, log, project_root  # noqa: E402


def _cpu_ram_info() -> dict:
    info = {"logical_cores": os.cpu_count() or 1}
    try:
        import psutil

        info["physical_cores"] = psutil.cpu_count(logical=False)
        vm = psutil.virtual_memory()
        info["total_ram_gb"] = round(vm.total / (1024**3), 2)
        info["available_ram_gb"] = round(vm.available / (1024**3), 2)
    except ImportError:
        info["physical_cores"] = None
        info["total_ram_gb"] = None
        info["available_ram_gb"] = None
        info["note"] = "psutil not installed yet (run `prepare`) - RAM figures unavailable"
    return info


def _disk_info(root: Path) -> dict:
    usage = shutil.disk_usage(root)
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
    }


def _find_models(models_dir: Path) -> list[str]:
    if not models_dir.exists():
        return []
    return [p.name for p in models_dir.glob("*.gguf")]


def diagnose() -> dict:
    root = project_root()
    manifest = load_manifest(root)

    bin_name = "llama-server.exe" if is_windows() else "llama-server"
    engine_binary = root / "runtime" / "bin" / bin_name
    venv_python = root / "runtime" / "venv" / ("Scripts/python.exe" if is_windows() else "bin/python3")
    models = _find_models(root / "models" / "llm")

    report = {
        "app_name": "LOCAL-LAB-AI",
        "os": {
            "name": platform.system(),
            "release": platform.release(),
            "arch": platform.machine(),
            "python_running_diagnose": platform.python_version(),
        },
        "cpu_ram": _cpu_ram_info(),
        "disk": _disk_info(root),
        "prepared": bool(manifest),
        "manifest": manifest,
        "venv_present": venv_python.exists(),
        "engine": {
            "binary_present": engine_binary.exists(),
            "binary_path": str(engine_binary) if engine_binary.exists() else None,
        },
        "models_found": models,
        "ocr_package_installed": _module_importable(venv_python, "rapidocr_onnxruntime"),
        "embeddings": "local hashing-trick embedder (no external model file required)",
        "project_root": str(root),
    }
    return report


def _module_importable(venv_python: Path, module: str) -> bool | str:
    if not venv_python.exists():
        return "unknown (venv not created yet - run `prepare`)"
    import subprocess

    result = subprocess.run(
        [str(venv_python), "-c", f"import {module}"], capture_output=True, timeout=30
    )
    return result.returncode == 0


def main() -> int:
    report = diagnose()
    print(json.dumps(report, indent=2, default=str))

    missing = []
    if not report["venv_present"]:
        missing.append("Python virtual environment (run `prepare`)")
    if not report["engine"]["binary_present"]:
        missing.append("llama.cpp engine binary (run `prepare`)")
    if not report["models_found"]:
        missing.append("LLM model file in models/llm/ (run `prepare`, or copy one manually)")
    if report["ocr_package_installed"] is not True:
        missing.append("OCR package (run `prepare`)")

    if missing:
        log("MISSING / NOT READY:")
        for m in missing:
            log(f"  - {m}")
        return 1

    log("All core components present. Run `start` to launch LOCAL-LAB-AI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
