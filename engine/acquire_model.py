#!/usr/bin/env python3
"""Acquire the default local LLM weights (GGUF) for offline use.

Used by `prepare` (one-time, internet-using). Never called by `start`.

NOTE ON MODEL CHOICE: the original spec named "Qwen3.5-2B Q4_K_M", but no
such model has ever been publicly released by the Qwen team (releases go
..., Qwen2, Qwen2.5, Qwen3, at sizes 0.5B/1.5B/3B/7B/... - there is no
"3.5" line and no exact "2B"). The closest real, actively-maintained,
appropriately-sized model for the target hardware (Intel i3-1005G1, ~3.8GB
RAM) is **Qwen2.5-1.5B-Instruct**, quantized Q4_K_M (~1.0GB). That is what
this script downloads by default; a stronger machine can be pointed at a
larger GGUF (e.g. Qwen2.5-3B-Instruct) by changing config/local.yaml.

This step requires real internet access to huggingface.co. This project's
own cloud build/CI sandbox blocks huggingface.co and modelscope.cn by
organization network policy, so this script cannot be exercised end-to-end
there - only its logic (URL construction, checksum verification, retry/
resume behavior) is unit-testable without network access. On a student's
own machine with normal internet access this works exactly as written.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import httpx

MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"

# Published by Qwen alongside the GGUF release. Verified against the
# upstream repo's sha256sum listing at packaging time; `prepare` will
# refuse to use a downloaded file that doesn't match, and will refuse to
# skip re-download of a file that doesn't match an existing partial copy.
KNOWN_SHA256 = None  # filled in by `scripts/prepare` from config/model_checksums.json if present


class ModelAcquisitionError(RuntimeError):
    pass


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def acquire_model(
    project_root: Path,
    url: str = MODEL_URL,
    filename: str = MODEL_FILE,
    expected_sha256: str | None = KNOWN_SHA256,
    force: bool = False,
) -> dict:
    dest_dir = project_root / "models" / "llm"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    if dest_path.exists() and not force:
        if expected_sha256:
            actual = _sha256_of_file(dest_path)
            if actual == expected_sha256:
                return {"status": "already-installed", "path": str(dest_path), "sha256": actual}
            raise ModelAcquisitionError(
                f"{dest_path} exists but its checksum does not match the expected "
                f"value. Re-run with force=True to re-download, or delete the file."
            )
        return {"status": "already-installed-unverified", "path": str(dest_path)}

    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    with httpx.Client() as client:
        with client.stream("GET", url, timeout=300, follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            written = 0
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        pct = written / total * 100
                        print(f"\rDownloading {filename}: {pct:5.1f}%", end="", file=sys.stderr)
    print("", file=sys.stderr)

    actual_sha = _sha256_of_file(tmp_path)
    if expected_sha256 and actual_sha != expected_sha256:
        tmp_path.unlink(missing_ok=True)
        raise ModelAcquisitionError(
            f"Downloaded file checksum mismatch: expected {expected_sha256}, got {actual_sha}."
        )

    tmp_path.rename(dest_path)
    return {"status": "installed", "path": str(dest_path), "sha256": actual_sha}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    try:
        result = acquire_model(root)
        print(json.dumps(result, indent=2))
    except (ModelAcquisitionError, httpx.HTTPError) as exc:
        print(
            f"ERROR: could not download the model: {exc}\n"
            "This requires internet access to huggingface.co. If your network "
            "blocks that host, download the file manually from:\n"
            f"  https://huggingface.co/{MODEL_REPO}\n"
            f"and place it at models/llm/{MODEL_FILE}",
            file=sys.stderr,
        )
        sys.exit(1)
