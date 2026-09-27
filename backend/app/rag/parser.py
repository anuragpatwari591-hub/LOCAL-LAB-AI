"""Document parsing and structure-aware chunking for local RAG.

Supported: .pdf, .docx, .txt, .md, and source code (.c, .cpp, .h, .hpp,
.java, .py, .sql, .js, .ts).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CODE_EXTENSIONS = {".c", ".cpp", ".h", ".hpp", ".java", ".py", ".sql", ".js", ".ts", ".cs"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}

# Boundaries that usually indicate a new logical unit in source code,
# used to avoid slicing a function/class in half where cheaply possible.
_CODE_BOUNDARY_RE = re.compile(
    r"^\s*(def |class |public |private |protected |static |void |int |"
    r"function |CREATE OR REPLACE|CREATE PROCEDURE|CREATE FUNCTION|"
    r"CREATE TRIGGER|BEGIN\b)",
    re.IGNORECASE,
)


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int
    metadata: dict


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext == ".docx":
        return _extract_docx(path)
    # Plain text, markdown, and all recognized source code extensions.
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages)


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _split_on_boundaries(text: str) -> list[str]:
    """Split code into logical blocks at likely function/class/procedure starts."""
    lines = text.splitlines()
    blocks: list[list[str]] = [[]]
    for line in lines:
        if _CODE_BOUNDARY_RE.match(line) and blocks[-1]:
            blocks.append([])
        blocks[-1].append(line)
    return ["\n".join(b) for b in blocks if b]


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 800,
    overlap: int = 120,
    is_code: bool = False,
) -> list[Chunk]:
    if not text.strip():
        return []

    units = _split_on_boundaries(text) if is_code else _paragraphs(text)

    chunks: list[Chunk] = []
    buffer = ""
    for unit in units:
        candidate = f"{buffer}\n\n{unit}".strip() if buffer else unit
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue

        if buffer:
            chunks.append(_make_chunk(buffer, source, len(chunks)))
            buffer = buffer[-overlap:] + "\n\n" + unit if overlap else unit
        else:
            # Single unit larger than chunk_size: hard-split with overlap.
            for piece in _sliding_window(unit, chunk_size, overlap):
                chunks.append(_make_chunk(piece, source, len(chunks)))
            buffer = ""

    if buffer.strip():
        chunks.append(_make_chunk(buffer, source, len(chunks)))

    return chunks


def _paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def _sliding_window(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


def _make_chunk(text: str, source: str, index: int) -> Chunk:
    return Chunk(text=text.strip(), source=source, chunk_index=index, metadata={})


def parse_and_chunk(path: Path, chunk_size: int = 800, overlap: int = 120) -> list[Chunk]:
    text = extract_text(path)
    is_code = path.suffix.lower() in CODE_EXTENSIONS
    return chunk_text(text, source=str(path.name), chunk_size=chunk_size, overlap=overlap, is_code=is_code)
