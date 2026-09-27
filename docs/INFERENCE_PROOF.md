# LOCAL-LAB-AI: llama.cpp inference plumbing proof

**Date:** 2026-09-27 (sandbox clock)
**Working dir:** `/tmp/inference-proof` (kept fully outside `/home/user/LOCAL-LAB-AI`)
**Verdict: real end-to-end inference through the actual llama.cpp engine was achieved.**
This is a **plumbing test only**. The model weights are randomly initialized
(never trained on any data), so every generated string below is gibberish by
design. What this proves is that the full chain works: a from-scratch HF
LLaMA-architecture checkpoint → locally-trained SentencePiece tokenizer →
`convert_hf_to_gguf.py` → valid GGUF file → real llama.cpp binaries (built
from the actual upstream source) → `llama-cli` text generation → `llama-server`
HTTP API (`/health`, `/completion`, `/v1/chat/completions`, SSE streaming).
It says nothing about answer quality — a real, pretrained Qwen GGUF would be
a drop-in replacement for `tiny-llama.gguf` in every step of this pipeline.

---

## 1. Environment / network reality check

- Sandbox blocks `huggingface.co`, `hf.co`, `modelscope.cn`, and (discovered
  along the way) `download.pytorch.org` — all confirmed 403 at the CCR
  agent-proxy layer (`gateway answered 403 to CONNECT`), not retried further.
- `pypi.org` works. `pip install torch --index-url https://pypi.org/simple`
  pulled the default GPU/CUDA-bundled wheel (`torch==2.14.0`) because the
  CPU-only wheel lives only on `download.pytorch.org` (blocked). We did not
  fight this further since torch runs fine on CPU regardless of which wheel
  variant is installed (the CUDA libraries are just unused, extra disk).
  Install took **2m15s**, ~5.4 GB in the venv.
- `api.github.com` and `https://github.com/...` (repo pages) are **blocked
  for repos not explicitly attached to the session** (a CCR-specific gate,
  independent of the general network policy) — confirmed both via `curl`
  and via `WebFetch`, both returning the CCR message
  `"GitHub access to this repository is not enabled for this session..."`.
  `add_repo(ggml-org/llama.cpp, access="read")` only unlocks anonymous
  `git clone`/`fetch` (which worked immediately), not the REST API or
  `github.com` page browsing. Escalating to `access="push"` (needed for API
  tools) was denied by the permission classifier. Per the task's own
  fallback instructions ("if API/asset lookup is infeasible, build from
  source"), **we built llama.cpp from source with cmake instead of
  downloading a release asset.** (`raw.githubusercontent.com` and
  `git clone` against `github.com` over the git protocol both work fine —
  only the HTML/API surface of `github.com`/`api.github.com` is gated.)

---

## 2. Tiny from-scratch LLaMA model + tokenizer

No network calls of any kind were used to build the model or tokenizer.

Corpus: `/tmp/inference-proof/corpus.txt` (16 short hand-written sentences,
~1.3 KB) used only to give a tokenizer trainer some vocabulary.

**Tokenizer** — trained locally with `sentencepiece.SentencePieceTrainer.train()`
(BPE, vocab_size=512, custom `<pad>/<unk>/<s>/</s>` ids 0/1/2/3):

```
sp.EncodeAsIds("local lab ai helps students")
  -> [23, 151, 23, 36, 5, 478, 383, 103]
sp.DecodeIds([...]) -> "local lab ai helps students"   # exact round trip
```

**Model** — `transformers.LlamaConfig` + `LlamaForCausalLM(config)` (random
init, `torch.manual_seed(42)`, no `from_pretrained`/hub access):

```
hidden_size=64, intermediate_size=128, num_hidden_layers=2,
num_attention_heads=2, num_key_value_heads=2, vocab_size=512,
max_position_embeddings=512
Total parameters: 147,776
```

Saved HF-format directory `tiny-llama-hf/`: `config.json`,
`generation_config.json`, `model.safetensors` (593 KB), `tokenizer.model`
(sentencepiece binary, 247 KB), `tokenizer.vocab`, `tokenizer_config.json`,
`special_tokens_map.json`.

**Caveat found and documented (not worked around silently):** this sandbox's
`transformers==5.17.0` ships a rewritten `LlamaTokenizer` that no longer
accepts a raw sentencepiece `vocab_file` the classic way — instantiating it
that way silently produces a near-empty 3-token vocab instead of erroring.
We caught this by comparing against `sentencepiece.SentencePieceProcessor`'s
own `GetPieceSize()` directly, and used that as the source of truth for
`vocab_size` in `LlamaConfig`. This does not block GGUF conversion because
`convert_hf_to_gguf.py`'s `_set_vocab_sentencepiece()` reads `tokenizer.model`
directly with `sentencepiece.SentencePieceProcessor` too, bypassing
`transformers`'s tokenizer classes entirely.

Script: `/tmp/inference-proof/build_model.py`.

---

## 3. HF -> GGUF conversion

```
git clone --depth 1 https://github.com/ggml-org/llama.cpp llama.cpp-src
# succeeded in 4.3s, commit 4da6337767f973e2b4d0797e5b323d77d8565e4a (2026-09-27)

python convert_hf_to_gguf.py /tmp/inference-proof/tiny-llama-hf \
  --outfile /tmp/inference-proof/artifacts/tiny-llama.gguf --outtype f16 --verbose
```

Ran successfully against the currently-installed `transformers 5.17.0` /
`torch 2.14.0` / `sentencepiece 0.2.2` / `gguf 0.19.0` (the repo's pinned
`requirements-convert_hf_to_gguf.txt` asks for older exact versions and
`torch==2.11.0` from the blocked `download.pytorch.org` index — we skipped
that pinned-requirements install, since the converter only needs
`transformers.AutoConfig` for config parsing plus `sentencepiece`/`torch`
directly, and it ran without errors against the newer versions already
installed).

Output: 21 tensors (2 transformer blocks + embeddings/output/norms),
GGUF v3, magic `GGUF`, **file size 309,376 bytes (302 KiB)**,
sha256 `40f2df3b9babeeab06ebfd1f93dda46514d2c6247f37a7da31c102f6a384174e`.

---

## 4. llama.cpp binary: source build (fallback path, see §1)

```
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF
cmake --build build --config Release -j4 --target llama-cli llama-server
```

- Toolchain: cmake 3.28.3, g++ 13.3.0 (Ubuntu 24.04), CPU backend only
  (`ggml-cpu` with SSE4.2/F16C/FMA/BMI2/AVX/AVX2 — no CUDA/Vulkan/Metal).
- Build time: **3m15s** wall clock (`user 10m11s` across 4 cores).
- llama.cpp version string embedded in binaries: `0.5.0-dev`, ggml commit
  `4da6337`, tag base `b1` (this is a from-source build, so it does not carry
  an official numbered release tag the way a downloaded release asset would).
- Binaries + their runtime `.so` dependencies collected in
  `artifacts/llama-cpp-bin/`:

```
llama-cli            1,430,552 bytes  sha256 2b5068b4a203719777e05c66d3b7363a7f2066c23941da83d4fbc7aeff589b2f
llama-server             17,888 bytes  sha256 45dbc83aea3e78070af248a34f67fe5601f816a02c23c3473c6e65430a4c2195
libggml-base.so.0.25.3      948,848 bytes
libggml-cpu.so.0.25.3      1,406,024 bytes
libggml.so.0.25.3            60,720 bytes
libllama.so.0.5.0         4,744,576 bytes
libllama-common.so.0.5.0  6,233,736 bytes
libmtmd.so.0.5.0          1,978,992 bytes
libllama-cli-impl.so        243,032 bytes
libllama-server-impl.so   3,942,072 bytes
```
Total `artifacts/llama-cpp-bin/` directory: **21 MB**.

(Coordinator later confirmed a direct-download path also works — e.g.
`https://github.com/ggml-org/llama.cpp/releases/download/b11222/llama-b11222-bin-ubuntu-x64.tar.gz`
via plain `curl -L`, bypassing the api.github.com/github.com page gate
entirely. We did not redo the binary via that path since the source build
had already completed and produced a working, verified binary; either path
is a legitimate "real prebuilt/real-compiled llama.cpp", not a simulation.)

---

## 5. Real inference: `llama-cli`

Note: this build of `llama-cli` runs in chat/conversation mode only (no
legacy raw-completion `-no-cnv` flag exists any more); a trivial pass-through
Jinja chat template was supplied since the untrained GGUF has no chat
template metadata (`unordered_map::at` otherwise, from a template registry
lookup on missing metadata — documented, not silently hidden).

```
./llama-cli -m /tmp/inference-proof/artifacts/tiny-llama.gguf \
  -p "Local Lab AI is" -n 20 --temp 0.8 --seed 42 --single-turn --no-jinja
  # -> unordered_map::at error (no chat template / newline token in this
  #    minuscule untrained vocab) -- reran with an explicit trivial template:

./llama-cli -m /tmp/inference-proof/artifacts/tiny-llama.gguf \
  -p "Local Lab AI is" -n 20 --temp 0.8 --seed 42 --single-turn --jinja \
  --chat-template "{% for m in messages %}{{ m['content'] }}{% endfor %}"
```

Full console output:

```
Loading model... |-\

 ...(llama.cpp ASCII banner)...

build      : b1-4da6337
model      : /tmp/inference-proof/artifacts/tiny-llama.gguf
ftype      : F16
modalities : text

> Local Lab AI is
vesfoad more Eng systemspsrown abjuith prove i syst answers everyeanGUg Tech

[ Prompt: 1761.8 t/s | Generation: 3471.6 t/s ]

Exiting...
```

This confirms: GGUF load succeeded, tokenizer (SPM, warns "newline token not
found" — expected for a 512-token toy vocab, falls back gracefully), forward
pass through both transformer blocks, sampling, and detokenization all work.
Output is nonsense English-looking word fragments, as expected from random
weights trained on nothing — exactly the intended result of this test.

---

## 6. Real inference: `llama-server`

```
./llama-server -m /tmp/inference-proof/artifacts/tiny-llama.gguf \
  --host 127.0.0.1 --port 8712 -c 512 --jinja \
  --chat-template "{% for m in messages %}{{ m['content'] }}{% endfor %}"
```

**`/health`:**
```
$ curl http://127.0.0.1:8712/health
{"status":"ok"}
```

**`/completion`** (`{"prompt":"Local Lab AI is","n_predict":20,"temperature":0.8,"seed":42}`)
— note the content is byte-for-byte identical to the `llama-cli` run above
with the same seed/prompt, confirming deterministic, consistent inference
across both binaries:
```json
{
  "index": 0,
  "content": "vesfoad more Eng systemspsrown abjuith prove i syst answers everyeanGUg Tech",
  "tokens_predicted": 20,
  "tokens_evaluated": 5,
  "prompt": "<s> Local Lab AI is",
  "stop_type": "limit",
  "timings": {
    "prompt_ms": 38.632, "prompt_per_second": 129.43,
    "predicted_ms": 2.299, "predicted_per_second": 8264.46
  }
}
```

**`/v1/chat/completions`** (OpenAI-compatible;
`{"model":"tiny-llama","messages":[{"role":"user","content":"Local Lab AI is"}],"max_tokens":20,"temperature":0.8,"seed":42}`):
```json
{
  "choices": [{
    "finish_reason": "length",
    "index": 0,
    "message": {"role": "assistant", "content": "vesfoad more Eng systemspsrown abjuith prove i syst answers everyeanGUg Tech"}
  }],
  "object": "chat.completion",
  "usage": {"completion_tokens": 20, "prompt_tokens": 5, "total_tokens": 25},
  "system_fingerprint": "b1-4da6337"
}
```
(First attempt against a server started *without* `--chat-template` failed
with `{"error":{"code":400,"message":"unordered_map::at",...}}` — same root
cause as §5, same fix. Documented rather than hidden.)

**Streaming SSE** (`/completion` with `"stream": true`, prompt "Operating
systems are", `n_predict=15`, seed 7) — 15 `data: {...}` events, one per
token, terminated by a final `"stop":true` event with full timing/usage
metadata (saved verbatim in `streaming-response.txt`, 32 lines). Example
line: `data: {"index":0,"content":" ser","tokens":[320],"stop":false,...}`.

Full raw responses saved in `completion-response.json`,
`chat-completion-response.json`, `streaming-response.txt`, and server log in
`llama-server.log`.

---

## 7. File sizes summary

| Artifact | Size |
|---|---|
| `tiny-llama-hf/model.safetensors` | 593,256 bytes |
| `tiny-llama-hf/tokenizer.model` | 247,342 bytes |
| `tiny-llama-hf/` (whole dir) | 852 KB |
| `tiny-llama.gguf` (F16) | 309,376 bytes (302 KiB) |
| `llama-cli` binary | 1,430,552 bytes |
| `llama-server` binary | 17,888 bytes |
| `llama-cpp-bin/` (binaries + shared libs) | 21 MB |
| Python venv (torch + transformers + deps) | 5.4 GB |
| Total `/tmp/inference-proof` | 5.9 GB |
| Disk free after everything | 19 GB (started at 30 GB) |

## 8. Timing summary (wall clock)

| Step | Time |
|---|---|
| `pip install torch` (pypi.org, CUDA-bundled wheel) | 2m15s |
| `pip install transformers sentencepiece gguf protobuf` | ~20s |
| Tokenizer training + model construction + save | ~5s |
| `git clone --depth 1` llama.cpp | 4.3s |
| GGUF conversion | ~2s |
| cmake configure | 1.4s |
| cmake build (llama-cli + llama-server, 4 cores) | 3m15s |
| llama-cli inference (20 tokens) | <1s (banner load dominates) |
| llama-server start + health + completion + chat + streaming | ~10s |
| **Total wall clock, this whole exercise** | **~15-18 minutes** |

## 9. What would change with a real pretrained model

Nothing in this pipeline is toy-model-specific: swap `tiny-llama-hf/` for a
real Qwen (or any Llama-family) HF checkpoint of legitimate size, rerun the
identical `convert_hf_to_gguf.py` command, and the identical `llama-cli` /
`llama-server` binaries and API calls used here would produce coherent
answers instead of gibberish. The only blocker to doing that *in this
sandbox* is that `huggingface.co`/`modelscope.cn` (where real Qwen GGUF/HF
weights live) are blocked by organization network policy — not anything
about llama.cpp itself, which this document shows is fully functional here.
