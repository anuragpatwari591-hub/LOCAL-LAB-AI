#!/usr/bin/env python3
"""Copy the prepared, offline-ready LOCAL-LAB-AI distribution onto a USB drive.

Safety rules (never violated):
- Never formats a drive.
- Never deletes existing files on the target drive.
- Only ever writes inside a `LOCAL-LAB-AI/` subfolder on the target -
  never touches the drive root or any other existing folder on it.
- Always requires the user to explicitly confirm the exact target before
  copying a single byte.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import is_windows, load_manifest, log, project_root, sha256_of_file  # noqa: E402

EXCLUDE_DIRS = {".git", "runtime/_download", "runtime/_download_python", "logs", ".devvenv", "__pycache__"}


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def list_removable_drives_linux() -> list[dict]:
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,RM,SIZE,MOUNTPOINT,TRAN,FSTYPE"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    data = json.loads(result.stdout)
    drives = []

    def walk(devices):
        for dev in devices:
            is_removable = dev.get("rm") in (True, "1", 1)
            mountpoint = dev.get("mountpoint")
            if is_removable and mountpoint:
                drives.append({
                    "device": f"/dev/{dev['name']}",
                    "mountpoint": mountpoint,
                    "size": dev.get("size"),
                    "fstype": dev.get("fstype"),
                })
            if "children" in dev:
                walk(dev["children"])

    walk(data.get("blockdevices", []))
    return drives


def list_removable_drives_windows() -> list[dict]:
    try:
        result = subprocess.run(
            ["wmic", "logicaldisk", "where", "drivetype=2", "get", "deviceid,volumename,size", "/format:csv"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    drives = []
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split(",")
    for line in lines[1:]:
        parts = line.split(",")
        row = dict(zip(header, parts))
        device_id = row.get("DeviceID")
        if device_id:
            drives.append({
                "device": device_id,
                "mountpoint": device_id + "\\",
                "size": row.get("Size"),
                "fstype": None,
                "label": row.get("VolumeName"),
            })
    return drives


def list_removable_drives() -> list[dict]:
    return list_removable_drives_windows() if is_windows() else list_removable_drives_linux()


def copy_payload(root: Path, dest_root: Path) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for item in root.iterdir():
        rel = item.name
        if rel in {".git"}:
            continue
        dest_item = dest_root / rel
        if item.is_dir():
            if rel in ("logs",):
                continue
            shutil.copytree(
                item, dest_item, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_download", "_download_python"),
            )
        else:
            shutil.copy2(item, dest_item)


def verify_deployment(dest_root: Path, source_manifest: dict) -> list[str]:
    problems = []

    bin_name = "llama-server.exe" if is_windows() else "llama-server"
    engine_path = dest_root / "runtime" / "bin" / bin_name
    if not engine_path.exists():
        problems.append(f"Engine binary missing at destination: {engine_path}")
    elif source_manifest.get("engine", {}).get("installed_sha256"):
        actual = sha256_of_file(engine_path)
        expected = source_manifest["engine"]["installed_sha256"]
        if actual != expected:
            problems.append(f"Engine binary checksum mismatch: expected {expected}, got {actual}")

    ggufs = list((dest_root / "models" / "llm").glob("*.gguf"))
    if not ggufs:
        problems.append("No .gguf model file at destination")

    launcher = "start.bat" if is_windows() else "start.sh"
    if not (dest_root / launcher).exists():
        problems.append(f"Launcher missing at destination: {launcher}")

    return problems


def main() -> int:
    root = project_root()
    manifest = load_manifest(root)

    if not manifest:
        log("ERROR: manifest.json not found. Run `prepare` before `deploy-usb`.")
        return 1

    log("Scanning for removable drives ...")
    drives = list_removable_drives()

    if not drives:
        log("No removable drives detected. Plug in a USB drive and try again.")
        log("(If your drive genuinely isn't detected, copy the project folder manually - "
            "deploy-usb never guesses a target it can't positively identify.)")
        return 1

    log("Removable drives found:")
    for i, d in enumerate(drives):
        log(f"  [{i}] {d['mountpoint']}  size={d.get('size')}  fstype={d.get('fstype')}")

    try:
        choice = input("Enter the number of the drive to deploy to (or 'q' to cancel): ").strip()
    except EOFError:
        log("No input available; aborting (deploy-usb requires interactive confirmation).")
        return 1

    if choice.lower() == "q":
        log("Cancelled.")
        return 0

    try:
        drive = drives[int(choice)]
    except (ValueError, IndexError):
        log("Invalid selection. Aborting.")
        return 1

    payload_size = _dir_size_bytes(root)
    log(f"Payload size: {payload_size / (1024**3):.2f} GB")

    dest_root = Path(drive["mountpoint"]) / "LOCAL-LAB-AI"
    confirm = input(
        f"\nThis will COPY (never format/delete) LOCAL-LAB-AI into:\n  {dest_root}\n"
        f"Existing unrelated files on the drive will not be touched.\n"
        f"Type 'yes' to proceed: "
    ).strip()

    if confirm.lower() != "yes":
        log("Cancelled - no changes made.")
        return 0

    log(f"Copying to {dest_root} ...")
    copy_payload(root, dest_root)

    log("Verifying deployment ...")
    problems = verify_deployment(dest_root, manifest)

    if problems:
        log("DEPLOYMENT VERIFICATION FAILED:")
        for p in problems:
            log(f"  - {p}")
        return 1

    log(f"Deployment verified. On the target machine: cd into {dest_root} and run "
        f"{'start.bat' if is_windows() else './start.sh'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
