"""Image upload -> local OCR endpoint."""

from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..core import paths
from ..core.config import get_config
from ..ocr.engine import is_available, run_ocr
from ..ocr.preprocessing import preprocess_image

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@router.get("/status")
def ocr_status():
    return {"available": is_available()}


@router.post("")
async def ocr_image(file: UploadFile = File(...)):
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {suffix}")

    paths.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = paths.UPLOADS_DIR / f"{uuid.uuid4()}_raw{suffix}"
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cfg = get_config()
    processed_path = raw_path.with_name(raw_path.stem + "_processed.png")
    preprocess_image(raw_path, processed_path, max_dim=cfg.ocr.max_image_dim)

    try:
        result = run_ocr(processed_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return result
