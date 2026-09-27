#!/usr/bin/env python3
"""Acquire the llama.cpp inference engine binary for this platform.

Used by `prepare` (one-time, internet-using). Never called by `start`.

NETWORK NOTE: this deliberately does NOT call the GitHub REST API
(api.github.com). In this project's own cloud build sandbox that endpoint
is gated per-repository and returns 403 for repos the session hasn't been
explicitly granted API access to - and more generally, api.github.com can
be rate-limited or blocked by all sorts of institutional/campus networks
in ways plain HTTPS downloads are not. Instead:

1. The latest llama.cpp build tag (e.g. "b11222") is discovered with a
   plain `git ls-remote --tags`, which needs only anonymous git-over-HTTPS
   access - no API token, no api.github.com.
2. The release asset is fetched directly from its stable
   github.com/<owner>/<repo>/releases/download/<tag>/<asset> URL. This was
   verified working end-to-end against the real llama.cpp repo while
   building this project (see docs/INFERENCE_PROOF.md).

Design goals:
- Do not hardcode a single asset filename indefinitely: llama.cpp's build
  matrix has changed release asset naming before (e.g. from a CPU-generic
  .zip to a per-arch .tar.gz). A short list of candidate filename patterns
  is tried per platform, most-current first.
- Verify the archive actually extracts to the expected binary before
  declaring success.
- Fail with a clear, actionable message (not a stack trace) if the
  network is unavailable or no candidate asset matches, and never crash
  `prepare`'s other steps because of it.
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import httpx

REPO = "ggml-org/llama.cpp"
REPO_URL = f"https://github.com/{REPO}"

# Candidate release asset filenames per platform, current naming first,
# followed by older naming schemes this project has seen llama.cpp use.
# `{tag}` is substituted with the discovered build tag.
_ASSET_CANDIDATES = {
    "Linux": [
        "llama-{tag}-bin-ubuntu-x64.tar.gz",
        "llama-{tag}-bin-ubuntu-x64.zip",
        "llama-{tag}-bin-linux-x64.tar.gz",
    ],
    "Windows": [
        "llama-{tag}-bin-win-cpu-x64.zip",
        "llama-{tag}-bin-win-x64.zip",
        "llama-{tag}-bin-windows-x64.zip",
    ],
}

EXPECTED_BINARY = {
    "Windows": "llama-server.exe",
    "Linux": "llama-server",
}


class EngineAcquisitionError(RuntimeError):
    pass


def _latest_build_tag() -> str:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", REPO_URL],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise EngineAcquisitionError(f"Could not list llama.cpp tags via git: {exc}") from exc

    tags = re.findall(r"refs/tags/(b\d+)$", result.stdout, re.MULTILINE)
    if not tags:
        raise EngineAcquisitionError("No build tags (bNNNNN) found on the llama.cpp remote.")

    return max(tags, key=lambda t: int(t[1:]))


def _try_download(url: str, dest: Path, client: httpx.Client) -> bool:
    try:
        with client.stream("GET", url, timeout=180, follow_redirects=True) as resp:
            if resp.status_code != 200:
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return True
    except httpx.HTTPError:
        return False


def _extract(archive_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.name.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(dest_dir)
    elif archive_path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path) as tf:
            tf.extractall(dest_dir)
    else:
        raise EngineAcquisitionError(f"Unsupported archive format: {archive_path.name}")


def _locate_and_install_binary(extracted_dir: Path, bin_dir: Path, platform_name: str) -> Path:
    binary_name = EXPECTED_BINARY.get(platform_name, "llama-server")
    matches = list(extracted_dir.rglob(binary_name))
    if not matches:
        raise EngineAcquisitionError(
            f"Extracted archive did not contain '{binary_name}'. Contents (sample): "
            f"{[p.name for p in extracted_dir.rglob('*')][:30]}"
        )

    bin_dir.mkdir(parents=True, exist_ok=True)
    dest = bin_dir / binary_name

    # Copy the whole directory the binary lives in (shared libs, etc.)
    src_dir = matches[0].parent
    for item in src_dir.iterdir():
        target = bin_dir / item.name
        if item.is_file():
            shutil.copy2(item, target)

    if platform_name != "Windows":
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return dest


def acquire_engine(project_root: Path, platform_name: str | None = None) -> dict:
    platform_name = platform_name or platform.system()
    if platform_name not in _ASSET_CANDIDATES:
        raise EngineAcquisitionError(f"Unsupported platform: {platform_name}")

    bin_dir = project_root / "runtime" / "bin"
    existing = bin_dir / EXPECTED_BINARY[platform_name]
    if existing.exists():
        return {"status": "already-installed", "binary": str(existing)}

    tag = _latest_build_tag()
    download_dir = project_root / "runtime" / "_download"

    with httpx.Client() as client:
        for candidate in _ASSET_CANDIDATES[platform_name]:
            asset_name = candidate.format(tag=tag)
            url = f"{REPO_URL}/releases/download/{tag}/{asset_name}"
            archive_path = download_dir / asset_name

            if not _try_download(url, archive_path, client):
                continue

            extracted_dir = download_dir / "extracted"
            try:
                _extract(archive_path, extracted_dir)
                binary_path = _locate_and_install_binary(extracted_dir, bin_dir, platform_name)
            except EngineAcquisitionError:
                shutil.rmtree(download_dir, ignore_errors=True)
                continue

            shutil.rmtree(download_dir, ignore_errors=True)
            return {
                "status": "installed",
                "release_tag": tag,
                "asset_name": asset_name,
                "asset_url": url,
                "binary": str(binary_path),
            }

    raise EngineAcquisitionError(
        f"None of the candidate asset names matched a working download for llama.cpp "
        f"tag {tag} on {platform_name}. Asset naming may have changed upstream; update "
        f"_ASSET_CANDIDATES in engine/acquire_engine.py, or download the release manually "
        f"from {REPO_URL}/releases/tag/{tag} and place the '{EXPECTED_BINARY[platform_name]}' "
        f"binary (plus its accompanying shared libraries) in runtime/bin/."
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    try:
        result = acquire_engine(root)
        print(json.dumps(result, indent=2))
    except EngineAcquisitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
