from __future__ import annotations

from pathlib import Path
from typing import Any

from .subtitle_cropper import CropConfig, crop_for_ocr


def run_ocr_on_frame_records(frame_records: list[dict], crop_config: CropConfig) -> list[dict]:
    engine = _load_ocr_engine()
    output: list[dict] = []

    for record in frame_records:
        frame_path = Path(record["path"])
        ocr_path = crop_for_ocr(frame_path, crop_config)
        rows = _ocr_image(engine, ocr_path)
        if not rows:
            continue

        text = "".join(row["text"] for row in rows).strip()
        if not text:
            continue
        confidence = sum(row["confidence"] for row in rows) / len(rows)
        output.append(
            {
                "time": float(record["time"]),
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": rows[0].get("bbox"),
                "frame": record["frame"],
                "ocr_frame": ocr_path.name,
                "engine": engine[0],
            }
        )
    return output


def _load_ocr_engine() -> Any:
    try:
        from rapidocr_onnxruntime import RapidOCR

        return ("rapidocr", RapidOCR())
    except ImportError:
        pass

    try:
        from paddleocr import PaddleOCR

        return ("paddle", PaddleOCR(use_angle_cls=True, lang="ch"))
    except Exception:
        pass

    raise RuntimeError("No usable OCR engine found. Install rapidocr-onnxruntime or paddleocr.")


def _ocr_image(engine: Any, image_path: Path) -> list[dict]:
    name, instance = engine
    if name == "paddle":
        result = instance.ocr(str(image_path), cls=True)
        rows = result[0] if result else []
        output = []
        for row in rows or []:
            bbox, text_info = row
            text, confidence = text_info
            output.append({"text": str(text), "confidence": float(confidence), "bbox": bbox})
        return output

    result, _ = instance(str(image_path))
    output = []
    for row in result or []:
        bbox, text, confidence = row
        output.append({"text": str(text), "confidence": float(confidence), "bbox": bbox})
    return output
