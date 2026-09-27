"""Real OCR test: renders text into an image with Pillow and runs the actual
RapidOCR engine on it. Skips gracefully if the OCR extra isn't installed
(e.g. a minimal dev environment that only installed core requirements)."""

import pytest

rapidocr = pytest.importorskip("rapidocr_onnxruntime", reason="OCR extra not installed")

from app.ocr.engine import is_available, run_ocr  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


@pytest.mark.skipif(not is_available(), reason="OCR engine failed to initialize")
def test_ocr_extracts_text_from_rendered_image(tmp_path):
    img = Image.new("RGB", (500, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "SELECT * FROM students", fill="black")

    img_path = tmp_path / "test.png"
    img.save(img_path)

    result = run_ocr(img_path)
    assert "text" in result
    assert len(result["text"]) > 0
    # Don't assert exact OCR accuracy (font rendering varies by environment) -
    # just that *something* resembling the rendered content came back.
    assert "student" in result["text"].lower() or "SELECT" in result["text"]
