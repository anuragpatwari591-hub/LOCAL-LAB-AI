# Contributing to LOCAL-LAB-AI

## Development setup

```bash
git clone <this repo>
cd LOCAL-LAB-AI
python3 -m venv .devvenv
source .devvenv/bin/activate        # Windows: .devvenv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

Run the backend in dev mode (auto-reload):

```bash
LOCAL_LAB_AI_ROOT=$(pwd) PYTHONPATH=backend uvicorn app.main:app --reload
```

The dev setup is entirely separate from the packaged USB distribution
(`runtime/venv/`, created by `prepare`) — changes here never affect a
prepared deployment until you re-run `prepare`.

## Running tests

```bash
pytest            # full suite
ruff check backend engine scripts tests   # lint
```

Some integration tests (`tests/integration/test_engine_real_inference.py`,
`tests/integration/test_ocr_real.py`) skip automatically if the relevant
optional dependency/binary isn't installed. To run them for real:

```bash
python engine/acquire_engine.py   # downloads the real llama.cpp binary
pytest tests/integration/test_engine_real_inference.py -v
```

## Adding a new assistant mode

Add one entry to `MODES` in `backend/app/modes/definitions.py` and one
`<option>` in `frontend/static/index.html`'s mode selector. Add a test in
`tests/unit/test_modes.py` asserting the new mode ID is present.

## Adding a new document type to RAG

Extend `_ALLOWED_SUFFIXES` in `backend/app/api/routes_documents.py` and
`extract_text()` in `backend/app/rag/parser.py`.

## Code style

- No comments explaining *what* code does — only *why*, when the reason
  isn't obvious from the code itself.
- Keep functions small and single-purpose; prefer composing small modules
  (see `backend/app/rag/`, `backend/app/ocr/`) over large monolithic files.
- Run `ruff check` before committing; CI enforces it.

## Commit messages

Use conventional prefixes where they fit: `feat:`, `fix:`, `test:`,
`docs:`, `build:`, `refactor:`. Keep the first line under ~70 characters.

## Reporting bugs / requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`.
