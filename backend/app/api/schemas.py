"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    mode: str = "general"
    conversation_id: str | None = None
    project_id: str | None = None
    marks: int | None = Field(default=None, description="Exam mark value (1/2/5/10) to scale answer detail")
    use_rag: bool = False
    ocr_text: str | None = Field(default=None, description="Pre-extracted OCR text to attach as context")


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    rag_sources: list[dict] = []


class ConversationCreate(BaseModel):
    title: str = "New conversation"
    mode: str = "general"
    project_id: str | None = None


class ProjectCreate(BaseModel):
    name: str


class NoteCreate(BaseModel):
    content: str
    project_id: str | None = None
