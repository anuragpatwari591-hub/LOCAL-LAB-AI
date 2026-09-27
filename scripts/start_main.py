#!/usr/bin/env python3
"""Fully offline startup. No pip, no internet, no model download here -
everything must already exist because `prepare` was run once beforehand.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import find_python, load_manifest, log, project_root  # noqa: E402


def _read_server_settings(root: Path) -> tuple[str, int, bool]:
    """Read host/port/open_browser from config without requiring PyYAML to
    already be importable by whatever Python is launching this script."""
    import re

    host, port, open_browser = "127.0.0.1", 8000, True
    for cfg_name in ("local.yaml", "default.yaml"):
        cfg_path = root / "config" / cfg_name
        if not cfg_path.exists():
            continue
        text = cfg_path.read_text(encoding="utf-8")
        m = re.search(r'host:\s*"?([\d.]+)"?', text)
        if m:
            host = m.group(1)
        m = re.search(r"port:\s*(\d+)", text)
        if m:
            port = int(m.group(1))
        m = re.search(r"open_browser:\s*(true|false)", text)
        if m:
            open_browser = m.group(1) == "true"
    return host, port, open_browser


def main() -> int:
    root = project_root()
    os.chdir(root)
    log(f"Starting LOCAL-LAB-AI from {root}")

    manifest = load_manifest(root)
    if not manifest:
        log(
            "No manifest.json found - it looks like `prepare` has not been run yet. "
            "Run `prepare` once (requires internet) before using `start`."
        )

    python_bin = find_python(root)
    log(f"Using Python: {python_bin}")

    host, port, open_browser = _read_server_settings(root)

    env = os.environ.copy()
    env["LOCAL_LAB_AI_ROOT"] = str(root)
    env["PYTHONPATH"] = str(root / "backend")

    cmd = [
        python_bin, "-m", "uvicorn", "app.main:app",
        "--host", host, "--port", str(port),
    ]

    log(f"Launching backend: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, cwd=str(root), env=env)

    if open_browser:
        url = f"http://{host}:{port}/"
        for _ in range(60):
            try:
                import urllib.request

                urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1)
                break
            except Exception:
                time.sleep(1)
        try:
            webbrowser.open(url)
        except Exception:
            log(f"Could not auto-open a browser. Open {url} manually.")

    try:
        process.wait()
    except KeyboardInterrupt:
        log("Shutting down ...")
        process.terminate()
        process.wait(timeout=10)

    return process.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
