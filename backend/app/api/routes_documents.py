"""Document upload / RAG management endpoints."""

from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..core import paths
from ..core.config import get_config
from ..rag.store import VectorStore

router = APIRouter(prefix="/api/documents", tags=["documents"])

_vector_store = VectorStore()

_ALLOWED_SUFFIXES = {
    ".pdf", ".docx", ".txt", ".md", ".markdown",
    ".c", ".cpp", ".h", ".hpp", ".java", ".py", ".sql", ".js", ".ts", ".cs",
}


@router.post("")
async def upload_document(file: UploadFile = File(...), project_id: str | None = None):
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    paths.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = paths.UPLOADS_DIR / f"{uuid.uuid4()}_{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cfg = get_config()
    result = _vector_store.add_document(
        dest, project_id=project_id, chunk_size=cfg.rag.chunk_size, overlap=cfg.rag.chunk_overlap
    )
    return result


@router.get("")
def list_documents(project_id: str | None = None):
    return _vector_store.list_documents(project_id)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    _vector_store.delete_document(document_id)
    return {"status": "deleted"}


@router.get("/search")
def search_documents(q: str, project_id: str | None = None, top_k: int = 5):
    return _vector_store.search(q, top_k=top_k, project_id=project_id)
