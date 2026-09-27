# Security Policy

## Design principles

- The backend binds to `127.0.0.1` (loopback) only, by default and without
  exception unless a user explicitly edits `config/local.yaml` to set
  `server.allow_remote: true` and changes `server.host` — this is a
  deliberate opt-in, not a default.
- No telemetry, analytics, or usage reporting of any kind.
- No API key is required or accepted anywhere in this project.
- Generated code from the assistant is **never executed automatically**.
  `config` exposes `security.allow_code_execution` (default `false`); even
  if enabled in a future version, execution must be explicitly sandboxed
  and opt-in per action, never implicit.
- All document/image/chat data stays in local SQLite databases under
  `data/`, which is git-ignored and never transmitted anywhere.

## Supported versions

Only the latest `main` branch / latest tagged release receives security
fixes; this is a single-maintainer-scale educational project, not a
long-term-support product.

## Reporting a vulnerability

Please open a GitHub issue using the "Security" label, or, for anything
sensitive, contact the repository owner directly via their GitHub profile
rather than filing a public issue. Include:
- The affected file/endpoint.
- Steps to reproduce.
- Potential impact (e.g. "allows binding to a non-loopback interface
  without explicit opt-in", "allows path traversal in document upload").

Do not include real personal data, credentials, or exam content belonging
to others in a public report.

## Known, accepted risk surface

- `deploy-usb` interacts with removable media and requires explicit
  interactive confirmation before writing anything; it is not designed to
  run non-interactively/unattended.
- `prepare` downloads and executes a third-party binary (llama.cpp). Its
  origin (official GitHub releases of `ggml-org/llama.cpp`) is fixed in
  source and not user-configurable without editing `engine/acquire_engine.py`.
