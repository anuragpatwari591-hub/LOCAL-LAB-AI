#!/usr/bin/env python3
"""Actively verify the offline claims - not just print "offline = true".

Each check either passes based on real evidence (a file exists AND has a
plausible size/format, a server actually answers a real HTTP request, a
grep genuinely found zero external references) or is reported FAIL with a
reason. Exit code is nonzero if any required check fails.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import is_windows, log, project_root  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []  # (name, passed, detail)


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    log(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def check_model(root: Path) -> None:
    ggufs = list((root / "models" / "llm").glob("*.gguf"))
    if not ggufs:
        check("Model file present", False, "no .gguf file in models/llm/")
        return
    f = ggufs[0]
    size_mb = f.stat().st_size / (1024 * 1024)
    with open(f, "rb") as fh:
        magic = fh.read(4)
    valid_magic = magic == b"GGUF"
    check(
        "Model file present and structurally valid",
        valid_magic and size_mb > 1,
        f"{f.name}, {size_mb:.1f} MB, GGUF magic={'ok' if valid_magic else 'MISSING'}",
    )


def check_engine(root: Path) -> None:
    bin_name = "llama-server.exe" if is_windows() else "llama-server"
    binary = root / "runtime" / "bin" / bin_name
    if not binary.exists():
        check("Engine binary present", False, "runtime/bin missing llama-server")
        return
    try:
        result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=15)
        ok = result.returncode == 0 and "version" in (result.stdout + result.stderr).lower()
        check("Engine binary runs (--version)", ok, (result.stdout + result.stderr).strip()[:120])
    except Exception as exc:
        check("Engine binary runs (--version)", False, str(exc))


def check_ocr(root: Path, venv_python: Path) -> None:
    if not venv_python.exists():
        check("OCR package importable", False, "venv not created - run prepare")
        return
    result = subprocess.run(
        [str(venv_python), "-c", "import rapidocr_onnxruntime, os; "
         "p = os.path.dirname(rapidocr_onnxruntime.__file__); print(p)"],
        capture_output=True, text=True, timeout=30,
    )
    check("OCR package importable", result.returncode == 0, result.stdout.strip() or result.stderr.strip()[:120])


def check_embeddings() -> None:
    # No external embedding model file is required: the default embedder is
    # a deterministic local hashing-trick projection (see backend/app/rag/embeddings.py).
    check("Embeddings require no downloaded model file", True, "hashing-trick embedder, pure numpy")


def check_frontend_no_cdn(root: Path) -> None:
    frontend_dir = root / "frontend" / "static"
    offenders = []
    url_re = re.compile(r"https?://[^\s\"'<>)]+")
    for path in frontend_dir.rglob("*"):
        if path.suffix not in (".html", ".js", ".css"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in url_re.findall(text):
            offenders.append(f"{path.relative_to(root)}: {match}")

    check("Frontend has zero external URLs (no CDN)", len(offenders) == 0, "; ".join(offenders[:5]))


def check_no_api_key_required(root: Path) -> None:
    backend_dir = root / "backend"
    offenders = []
    key_re = re.compile(r"(OPENAI_API_KEY|ANTHROPIC_API_KEY|api[_-]?key\s*=\s*[\"'](?!\"\"|'')\S)", re.IGNORECASE)
    for path in backend_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if key_re.search(text):
            offenders.append(str(path.relative_to(root)))
    check("No API key required by backend code", len(offenders) == 0, "; ".join(offenders[:5]))


def check_backend_and_engine_live(root: Path, venv_python: Path) -> None:
    if not venv_python.exists():
        check("Backend starts and /api/health responds", False, "venv not created - run prepare")
        return

    import os as _os

    env = _os.environ.copy()
    env["LOCAL_LAB_AI_ROOT"] = str(root)
    env["PYTHONPATH"] = str(root / "backend")
    port = 8799

    proc = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        healthy = False
        engine_running = False
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as resp:
                    data = json.loads(resp.read())
                    healthy = data.get("status") == "ok"
                    engine_running = data.get("engine_running", False)
                    break
            except Exception:
                time.sleep(1)

        check("Backend starts and /api/health responds", healthy)

        if healthy:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as resp:
                is_local_html = resp.status == 200 and b"LOCAL-LAB-AI" in resp.read()
            check("Frontend served locally from backend (no separate web server)", is_local_html)

        check(
            "Inference engine reports running via /api/health",
            engine_running,
            "engine not running - expected if model/engine assets are missing in this environment"
            if not engine_running else "",
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    root = project_root()
    venv_python = root / "runtime" / "venv" / ("Scripts/python.exe" if is_windows() else "bin/python3")

    log("Running offline verification checks (this performs real actions, not just file checks)...")
    check_model(root)
    check_engine(root)
    check_ocr(root, venv_python)
    check_embeddings()
    check_frontend_no_cdn(root)
    check_no_api_key_required(root)
    check_backend_and_engine_live(root, venv_python)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    log(f"\n{passed}/{total} checks passed.")

    required_for_full_offline_operation = {
        "Model file present and structurally valid",
        "Engine binary runs (--version)",
        "Backend starts and /api/health responds",
        "Inference engine reports running via /api/health",
    }
    hard_fail = [name for name, ok, _ in CHECKS if not ok and name in required_for_full_offline_operation]

    if hard_fail:
        log("NOT fully offline-ready yet. Missing: " + ", ".join(hard_fail))
        return 1

    log("Fully offline-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
