"""Path portability: PROJECT_ROOT must never hardcode a drive/mount point."""

import importlib


def test_project_root_follows_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_LAB_AI_ROOT", str(tmp_path))
    from app.core import paths

    importlib.reload(paths)
    assert paths.PROJECT_ROOT == tmp_path.resolve()
    assert paths.MODELS_DIR == tmp_path.resolve() / "models"

    monkeypatch.delenv("LOCAL_LAB_AI_ROOT", raising=False)
    importlib.reload(paths)


def test_project_root_falls_back_to_file_location(monkeypatch):
    monkeypatch.delenv("LOCAL_LAB_AI_ROOT", raising=False)
    from app.core import paths

    importlib.reload(paths)
    # backend/app/core/paths.py -> repo root
    assert (paths.PROJECT_ROOT / "backend" / "app" / "core" / "paths.py").exists()
    assert (paths.PROJECT_ROOT / "frontend").exists()


def test_no_hardcoded_drive_letters_in_source():
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    offenders = []
    pattern = re.compile(r'["\']([A-Za-z]:\\\\|/mnt/[a-z]|/media/)')
    for path in (repo_root / "backend").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path))
    assert not offenders, f"Hardcoded absolute paths found: {offenders}"
