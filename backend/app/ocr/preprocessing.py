"""Lightweight local image preprocessing before OCR (resize, normalize orientation)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def preprocess_image(src_path: Path, dst_path: Path, max_dim: int = 1600) -> Path:
    with Image.open(src_path) as img:
        img = ImageOps.exif_transpose(img)  # respect phone-camera orientation metadata
        img = img.convert("RGB")

        width, height = img.size
        scale = min(1.0, max_dim / max(width, height))
        if scale < 1.0:
            img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst_path, format="PNG")

    return dst_path
