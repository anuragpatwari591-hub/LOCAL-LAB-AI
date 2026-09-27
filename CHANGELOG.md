# Changelog

## v1.0.0 (2026-09-27)

Initial release. Built autonomously in a cloud sandbox in a single pass; see
README.md's "Honest limitations" section for exactly what was executed and
verified in that sandbox versus implemented-but-unverified there.

### Added
- FastAPI backend with 9 B.Tech-focused assistant modes (general, OS/Linux
  lab, DBMS/Oracle SQL & PL-SQL, software engineering project, coding,
  debug, mark-aware exam, viva, document/RAG).
- Local llama.cpp-based inference engine integration, with resilient
  direct-URL binary acquisition (`engine/acquire_engine.py`) and model
  acquisition (`engine/acquire_model.py`, defaulting to Qwen2.5-1.5B-Instruct
  Q4_K_M).
- Local OCR pipeline (RapidOCR + ONNX Runtime), no separate model download.
- Local RAG pipeline: PDF/DOCX/TXT/MD/source-code parsing, structure-aware
  chunking, a deterministic hashing-trick embedder, SQLite+NumPy vector
  store.
- Local SQLite-backed conversation memory and project workspaces.
- Vanilla HTML/CSS/JS frontend with streaming chat, Markdown/code
  rendering, image/document upload - zero CDN dependencies.
- Cross-platform launchers (`start`/`prepare`/`diagnose`/`offline-check`/
  `deploy-usb`) as `.sh`/`.bat`/`.ps1`, all resolving their own directory
  portably (no hardcoded drive letters or paths).
- 80-test automated suite (unit, integration, launcher, and a real,
  non-mocked end-to-end llama.cpp inference test - see
  `docs/INFERENCE_PROOF.md`) plus GitHub Actions CI.
- Full documentation set: README, ARCHITECTURE, TROUBLESHOOTING,
  THIRD_PARTY_LICENSES, CONTRIBUTING, SECURITY, issue/PR templates.

### Known limitations
See README.md's "Honest limitations" table.
