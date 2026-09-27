# Troubleshooting

## "No Python interpreter found on PATH"

Install Python 3.10 or later:
- **Windows**: https://www.python.org/downloads/ — check "Add python.exe to PATH" during install.
- **Linux**: `sudo apt install python3 python3-venv` (Debian/Ubuntu) or your distro's equivalent.

Then re-run `prepare`.

## `prepare` fails to download the model

`engine/acquire_model.py` needs internet access to `huggingface.co`. If your
network blocks it (some campus/lab networks do), `prepare` will print a
manual download link. Download the file and place it at:

```
models/llm/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

Then re-run `prepare` (or just `start` directly — it only needs the file
to exist).

## `prepare` fails to download the engine binary

`engine/acquire_engine.py` tries several known llama.cpp release asset
names against the latest build tag. If llama.cpp's release asset naming has
changed again, the error message names the exact URLs tried. Download the
matching `llama-*-bin-ubuntu-x64.tar.gz` (Linux) or `llama-*-bin-win-cpu-x64.zip`
(Windows) release asset manually from
https://github.com/ggml-org/llama.cpp/releases, extract it, and copy
`llama-server` (plus the `.so`/`.dll` files next to it) into `runtime/bin/`.

## The UI says "Local inference engine is not running"

Run `./offline-check.sh` (or `.\offline-check.bat`) — it will tell you
specifically which of: engine binary, model file, or backend startup is the
problem. Check `logs/engine.log` for the llama-server process's own output.

## OCR fails / "OCR engine is not available"

`prepare` should have installed `rapidocr-onnxruntime`, which bundles its
own ONNX models inside the pip wheel (no separate download needed). If it's
missing, re-run `prepare`, or manually: `runtime/venv/bin/pip install rapidocr-onnxruntime onnxruntime`.

## Port already in use

Another process is using port 8000 (or the configured `engine_port`,
default 8712). Edit `config/local.yaml` (create it if it doesn't exist) to
set a different `server.port` / `llm.engine_port`.

## Everything looks installed but answers are gibberish

Check `diagnose` output for which model file is actually loaded. If it's
`tests/fixtures/tiny_model/tiny-llama.gguf` or any file other than a real
Qwen GGUF, that's the tiny structural-test fixture from this project's own
test suite (see `docs/INFERENCE_PROOF.md`) — it has *random, untrained*
weights and will never produce sensible text. Run `prepare` to fetch the
real model into `models/llm/`.

## USB drive not detected by `deploy-usb`

`deploy-usb` only ever acts on a drive it can positively identify via
`lsblk` (Linux) or `wmic` (Windows). If your drive genuinely isn't
detected, copy the `LOCAL-LAB-AI/` folder to the drive manually — the
tool intentionally never guesses.
