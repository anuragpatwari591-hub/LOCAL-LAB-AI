import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

for p in (REPO_ROOT / "backend", REPO_ROOT / "scripts", REPO_ROOT / "engine"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Isolate the test run's PROJECT_ROOT from the real dev checkout so API/
# integration tests don't read or write real conversation history, uploaded
# documents, etc. Backend/frontend/config code is reused via symlink (it's
# what's under test); data/models/runtime get fresh empty directories.
_test_root = Path(tempfile.mkdtemp(prefix="local_lab_ai_test_root_"))
for shared in ("backend", "frontend", "config"):
    (_test_root / shared).symlink_to(REPO_ROOT / shared)
for isolated in ("data/memory", "data/uploads", "data/projects", "models/llm", "logs"):
    (_test_root / isolated).mkdir(parents=True, exist_ok=True)

# runtime/bin (the llama.cpp engine binary, if `prepare`/acquire_engine.py has
# been run against the real repo) is read-only test input, not test output,
# so it's safe and useful to share rather than isolate.
(_test_root / "runtime").mkdir(parents=True, exist_ok=True)
_real_bin = REPO_ROOT / "runtime" / "bin"
if _real_bin.exists() and any(_real_bin.iterdir()):
    (_test_root / "runtime" / "bin").symlink_to(_real_bin)
else:
    (_test_root / "runtime" / "bin").mkdir(parents=True, exist_ok=True)

os.environ["LOCAL_LAB_AI_ROOT"] = str(_test_root)
