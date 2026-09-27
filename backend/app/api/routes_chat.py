"""Chat endpoints: streaming completions grounded in mode + memory + optional RAG."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..core.config import get_config
from ..engine.manager import EngineNotReadyError, get_engine
from ..memory.store import MemoryStore, history_to_chat_messages
from ..modes.definitions import get_mode, list_modes
from ..rag.retriever import build_context_block
from ..rag.store import VectorStore
from .schemas import ChatRequest, ConversationCreate

router = APIRouter(prefix="/api", tags=["chat"])

_memory = MemoryStore()
_vector_store = VectorStore()


def _marks_hint(marks: int | None) -> str:
    if marks is None:
        return ""
    guidance = {
        1: "This question is worth 1 mark: answer in one or two lines only, no headers.",
        2: "This question is worth 2 marks: answer in a short, tight paragraph.",
        5: "This question is worth 5 marks: give a structured answer with 4-6 bullet points.",
        10: "This question is worth 10 marks: give a detailed, multi-section answer with code/diagram where relevant.",
    }
    return guidance.get(
        marks, f"This question is worth {marks} marks: scale your answer's length and detail accordingly."
    )


@router.get("/modes")
def get_modes():
    return [{"id": m.id, "label": m.label, "description": m.description} for m in list_modes()]


@router.post("/conversations")
def create_conversation(body: ConversationCreate):
    conv_id = _memory.create_conversation(body.title, body.mode, body.project_id)
    return {"conversation_id": conv_id}


@router.get("/conversations")
def list_conversations(project_id: str | None = None):
    return _memory.list_conversations(project_id)


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    cfg = get_config()
    return _memory.get_history(conversation_id, limit=cfg.memory.max_history_messages * 4)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    _memory.clear_conversation(conversation_id)
    return {"status": "deleted"}


def _build_messages(req: ChatRequest, conversation_id: str) -> tuple[list[dict], list[dict]]:
    cfg = get_config()
    mode = get_mode(req.mode)
    system_prompt = mode.system_prompt

    marks_hint = _marks_hint(req.marks)
    if marks_hint:
        system_prompt = f"{system_prompt}\n\n{marks_hint}"

    rag_sources: list[dict] = []
    if req.use_rag and cfg.rag.enabled:
        context_block, rag_sources = build_context_block(
            _vector_store, req.message, top_k=cfg.rag.top_k, project_id=req.project_id
        )
        if context_block:
            system_prompt = f"{system_prompt}\n\n{context_block}"

    history = _memory.get_history(conversation_id, limit=cfg.memory.max_history_messages)
    chat_history = history_to_chat_messages(history)

    user_content = req.message
    if req.ocr_text:
        user_content = f"{req.message}\n\n[OCR-extracted text from attached image]:\n{req.ocr_text}"

    messages = [{"role": "system", "content": system_prompt}, *chat_history, {"role": "user", "content": user_content}]
    return messages, rag_sources


@router.post("/chat")
async def chat(req: ChatRequest):
    cfg = get_config()

    conversation_id = req.conversation_id
    if not conversation_id:
        title = req.message[:60]
        conversation_id = _memory.create_conversation(title=title, mode=req.mode, project_id=req.project_id)

    _memory.add_message(conversation_id, "user", req.message, ocr_text=req.ocr_text)

    messages, rag_sources = _build_messages(req, conversation_id)

    engine = get_engine()
    if not engine.is_running():
        raise HTTPException(
            status_code=503,
            detail="Local inference engine is not running. Restart the app with `start`.",
        )

    async def event_stream():
        full_response = []
        meta = {"type": "meta", "conversation_id": conversation_id, "rag_sources": rag_sources}
        yield f"data: {json.dumps(meta)}\n\n"
        try:
            async for delta in engine.chat_completion_stream(
                messages, max_tokens=cfg.llm.max_tokens, temperature=cfg.llm.temperature
            ):
                full_response.append(delta)
                yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
        except EngineNotReadyError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            return

        answer = "".join(full_response)
        _memory.add_message(conversation_id, "assistant", answer)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/memory/clear")
def clear_memory():
    _memory.clear_all()
    return {"status": "cleared"}
