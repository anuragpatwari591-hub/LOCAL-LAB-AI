"""Real (not mocked) end-to-end inference test against the actual llama.cpp
engine, using a tiny structurally-valid GGUF fixture (random/untrained
weights - see docs/INFERENCE_PROOF.md for how it was built and why).

This exercises the real binary + real GGUF loading + real HTTP server, the
same code path `LlamaEngine` uses in production against a real Qwen model.
It only checks that the plumbing works (a well-formed response comes back),
never that the output is semantically correct - that would require real
trained weights, which this fixture deliberately does not have.

Skipped if runtime/bin/llama-server hasn't been installed (e.g. a minimal
dev checkout that hasn't run `prepare` / engine/acquire_engine.py). CI runs
that acquisition step explicitly so this test executes for real there.
"""

from pathlib import Path

import pytest
from app.core.config import LLMConfig
from app.engine.manager import EngineNotReadyError, LlamaEngine, find_engine_binary

FIXTURE_MODEL = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_model" / "tiny-llama.gguf"


def _engine_available() -> bool:
    return find_engine_binary() is not None and FIXTURE_MODEL.exists()


@pytest.mark.skipif(not _engine_available(), reason="engine binary not installed (run engine/acquire_engine.py)")
async def test_real_llama_server_starts_and_answers(tmp_path, monkeypatch):
    # Point model discovery at our tiny fixture instead of a real Qwen model.
    monkeypatch.setattr(
        "app.engine.manager.find_model_file",
        lambda _filename: FIXTURE_MODEL,
    )

    config = LLMConfig(
        model_file="tiny-llama.gguf",
        context_size=256,
        threads=2,
        batch_size=64,
        engine_port=8792,
        max_tokens=8,
    )
    engine = LlamaEngine(config)

    engine.start()
    try:
        assert engine.wait_until_healthy(timeout_s=30), "engine did not report healthy"

        # Note: /v1/chat/completions (engine.chat_completion) applies a chat
        # template, which this minimal 512-token proof-of-concept vocabulary
        # doesn't fully support (it has no real chat special tokens - a real
        # Qwen GGUF does). So this test proves the plumbing via the native
        # /completion endpoint instead; see docs/INFERENCE_PROOF.md.
        answer = await engine.complete_raw("local lab ai", max_tokens=8)
        assert isinstance(answer, str)
        assert len(answer) > 0
    finally:
        engine.stop()


@pytest.mark.skipif(not _engine_available(), reason="engine binary not installed (run engine/acquire_engine.py)")
def test_engine_reports_not_ready_before_start():
    config = LLMConfig(model_file="tiny-llama.gguf", engine_port=8793)
    engine = LlamaEngine(config)
    assert not engine.is_running()
    with pytest.raises(EngineNotReadyError):
        _ = engine.base_url
