# Architecture

## Request flow

```
Browser (frontend/static/*.html/js/css, same-origin, no CDN)
   │  fetch()/SSE
   ▼
FastAPI app (backend/app/main.py), bound to 127.0.0.1
   ├── api/routes_chat.py      -> modes + memory + optional RAG context -> engine
   ├── api/routes_documents.py -> rag/parser.py -> rag/embeddings.py -> rag/store.py
   ├── api/routes_ocr.py       -> ocr/preprocessing.py -> ocr/engine.py (RapidOCR)
   └── api/routes_meta.py      -> projects/notes/health/diagnostics
   │
   ▼
engine/manager.py (LlamaEngine)
   │  subprocess, loopback only
   ▼
runtime/bin/llama-server (real llama.cpp release binary)
   │  loads
   ▼
models/llm/*.gguf (Qwen2.5-1.5B-Instruct Q4_K_M by default)
```

## Why a hashing embedder instead of a neural embedding model

Every other local-RAG tutorial reaches for a Hugging Face sentence-transformer.
This project deliberately does not, for two reasons that turned out to
reinforce each other:

1. **Network reality**: this project's own build/CI sandbox blocks
   huggingface.co outright, and unpredictable campus/lab network policies
   are common in the target environment (student laptops on college wifi).
2. **Product requirement**: `start` must work with *zero* network calls,
   forever, not just on day one.

`backend/app/rag/embeddings.py` implements the feature-hashing trick (a
deterministic bag-of-words → fixed-dimension vector projection, in the same
family as scikit-learn's `HashingVectorizer`): each token is SHA-256-hashed
into one of N buckets with a deterministic sign, weighted by log-scaled term
frequency, and L2-normalized. It needs no model file, no download, and no
GPU. It's less semantically rich than a trained embedding model (it won't
catch synonyms it's never seen combined before), but for a single student's
own lab notes/PDFs/source files, keyword/n-gram overlap does most of the
useful work, and it's real, fast, and provably offline. The interface
(`BaseEmbedder`) is small enough that a stronger local embedding backend
(e.g. a GGUF embedding model run through the same llama.cpp engine) could
be swapped in later without touching any caller.

## Why the engine is acquired via direct release URLs, not the GitHub API

See `engine/acquire_engine.py`'s docstring in full, but in short:
`api.github.com` is blocked/gated in more environments (including this
project's own build sandbox) than plain `github.com/.../releases/download/...`
URLs are. The latest build tag is discovered with `git ls-remote --tags`
(anonymous, no API token needed), and the asset is downloaded directly, with
a short list of candidate filenames tried in order in case llama.cpp's
release asset naming changes again (it has, at least twice in this
project's own testing).

## Why `start` requires Python 3.10+ already installed

The original ambition was a fully self-contained runtime (no host Python at
all), using `python-build-standalone`'s prebuilt interpreters. That repo's
GitHub release assets turned out to be gated by the same per-repository
access control that blocked `api.github.com` for `ggml-org/llama.cpp` (see
`README.md`'s "Honest limitations" section) — and unlike llama.cpp, its
build artifacts aren't in the git repo itself (no source-based fallback).
Given the target machines (B.Tech lab PCs, personal laptops) essentially
always have *some* Python already, the pragmatic and honest choice was: one
prerequisite (Python 3.10+), and `prepare` builds an isolated virtualenv
(`runtime/venv/`) with every dependency pinned and pre-installed, so `start`
itself never touches pip or the internet.

## Modes

`backend/app/modes/definitions.py` is a flat table of system prompts. Adding
a mode is a matter of adding one `Mode(...)` entry and one frontend
`<option>` — there is no plugin system because a fixed set of B.Tech-relevant
modes was the actual requirement, not general extensibility.
