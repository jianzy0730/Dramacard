from __future__ import annotations

import re


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
PURE_EN_RE = re.compile(r"^[A-Za-z]+$")
PURE_NUM_RE = re.compile(r"^\d+$")
NOISE_SYMBOL_RE = re.compile(r"[^\w\u4e00-\u9fff，。！？、：；“”‘’《》…·（）()【】\-\s]")


def clean_ocr_records(records: list[dict], min_confidence: float = 0.65) -> list[dict]:
    cleaned: list[dict] = []
    for record in records:
        confidence = float(record.get("confidence") or 0.0)
        if confidence < min_confidence:
            continue

        text = normalize_text(str(record.get("text", "")))
        if not text or is_noise_text(text):
            continue

        item = dict(record)
        item["raw_text"] = record.get("text", "")
        item["text"] = text
        item["confidence"] = round(confidence, 4)
        cleaned.append(item)
    return cleaned


def normalize_text(text: str) -> str:
    text = text.strip()
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", "", text)
    text = NOISE_SYMBOL_RE.sub("", text)
    return text.strip()


def is_noise_text(text: str) -> bool:
    if len(text) <= 1:
        return True
    if PURE_NUM_RE.fullmatch(text):
        return True
    if PURE_EN_RE.fullmatch(text) and len(text) <= 8:
        return True
    if not CHINESE_RE.search(text) and len(text) <= 8:
        return True
    lowered = text.lower()
    watermark_words = ["抖音", "快手", "douyin", "kuaishou", "bilibili"]
    return any(word in lowered for word in watermark_words)
