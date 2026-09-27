"""Local OCR via RapidOCR + ONNX Runtime.

RapidOCR ships its detection/classification/recognition ONNX models as
package data inside the `rapidocr-onnxruntime` PyPI wheel itself, so once
`prepare` has pip-installed it (from PyPI, which this project always treats
as reachable during the one-time preparation step), OCR works completely
offline at runtime with zero additional downloads and no Hugging Face
dependency.

Import is lazy so the rest of the backend (chat, RAG, memory) works even in
minimal dev/CI environments where the OCR extra is not installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_engine_singleton: Any = None
_import_error: Exception | None = None


def _get_engine():
    global _engine_singleton, _import_error
    if _engine_singleton is not None:
        return _engine_singleton
    if _import_error is not None:
        raise _import_error
    try:
        from rapidocr_onnxruntime import RapidOCR

        _engine_singleton = RapidOCR()
        return _engine_singleton
    except Exception as exc:  # pragma: no cover - exercised only when dependency missing
        _import_error = exc
        raise


def is_available() -> bool:
    try:
        _get_engine()
        return True
    except Exception:
        return False


def run_ocr(image_path: Path) -> dict:
    """Run OCR on an image file. Returns extracted text plus per-line detail.

    Raises RuntimeError with a clear message if the OCR dependency/models
    are not installed, instead of silently returning empty text.
    """
    try:
        engine = _get_engine()
    except Exception as exc:
        raise RuntimeError(
            "OCR engine is not available. Run `prepare` to install the "
            "rapidocr-onnxruntime package, which bundles its own local "
            "ONNX models (no separate download needed)."
        ) from exc

    result, _elapse = engine(str(image_path))
    if not result:
        return {"text": "", "lines": []}

    lines = [{"text": r[1], "confidence": float(r[2]), "box": r[0]} for r in result]
    full_text = "\n".join(line["text"] for line in lines)
    return {"text": full_text, "lines": lines}
