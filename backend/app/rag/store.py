"""Local vector store: SQLite for metadata/text, NumPy arrays for vectors.

No cloud vector database, no network calls. Vectors are stored as raw
float32 bytes in a BLOB column and reconstructed with numpy.frombuffer.
Suitable for the document collection sizes a single student accumulates
(hundreds to low thousands of chunks) on a low-end laptop.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from ..core import paths
from .embeddings import BaseEmbedder, cosine_similarity, get_default_embedder
from .parser import Chunk, parse_and_chunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    filename TEXT NOT NULL,
    added_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    project_id TEXT,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
"""


class VectorStore:
    def __init__(self, db_path: Path | None = None, embedder: BaseEmbedder | None = None, dim: int = 256):
        paths.ensure_data_dirs()
        self.db_path = db_path or (paths.MEMORY_DIR / "rag.db")
        self.embedder = embedder or get_default_embedder(dim=dim)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def add_document(
        self,
        file_path: Path,
        project_id: str | None = None,
        chunk_size: int = 800,
        overlap: int = 120,
    ) -> dict:
        chunks = parse_and_chunk(file_path, chunk_size=chunk_size, overlap=overlap)
        doc_id = str(uuid.uuid4())

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO documents (id, project_id, filename, added_at) VALUES (?, ?, ?, ?)",
                (doc_id, project_id, file_path.name, time.time()),
            )
            for chunk in chunks:
                self._insert_chunk(conn, doc_id, project_id, chunk)

        return {"document_id": doc_id, "filename": file_path.name, "chunk_count": len(chunks)}

    def _insert_chunk(self, conn: sqlite3.Connection, doc_id: str, project_id: str | None, chunk: Chunk) -> None:
        vector = self.embedder.embed(chunk.text)
        conn.execute(
            "INSERT INTO chunks (id, document_id, project_id, chunk_index, text, embedding, embedding_dim) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                doc_id,
                project_id,
                chunk.chunk_index,
                chunk.text,
                vector.astype(np.float32).tobytes(),
                vector.shape[0],
            ),
        )

    def list_documents(self, project_id: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE project_id = ? ORDER BY added_at DESC", (project_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM documents ORDER BY added_at DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, document_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def search(self, query: str, top_k: int = 5, project_id: str | None = None) -> list[dict]:
        query_vec = self.embedder.embed(query)

        with self._conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT c.text, c.embedding, c.chunk_index, d.filename "
                    "FROM chunks c JOIN documents d ON c.document_id = d.id "
                    "WHERE c.project_id = ?",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT c.text, c.embedding, c.chunk_index, d.filename "
                    "FROM chunks c JOIN documents d ON c.document_id = d.id"
                ).fetchall()

        scored = []
        for row in rows:
            vec = np.frombuffer(row["embedding"], dtype=np.float32)
            score = cosine_similarity(query_vec, vec)
            scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, row in scored[:top_k]:
            results.append(
                {
                    "score": round(score, 4),
                    "text": row["text"],
                    "source": row["filename"],
                    "chunk_index": row["chunk_index"],
                }
            )
        return results

    def clear(self, project_id: str | None = None) -> None:
        with self._conn() as conn:
            if project_id:
                conn.execute("DELETE FROM chunks WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
            else:
                conn.executescript("DELETE FROM chunks; DELETE FROM documents;")
