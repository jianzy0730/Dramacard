from __future__ import annotations

import difflib


def merge_subtitles(
    records: list[dict],
    frame_interval: float,
    similarity_threshold: float = 0.85,
) -> list[dict]:
    if not records:
        return []

    sorted_records = sorted(records, key=lambda item: float(item["time"]))
    merged: list[dict] = []
    current = _new_event(sorted_records[0])
    last_time = float(sorted_records[0]["time"])

    for record in sorted_records[1:]:
        text = str(record["text"])
        time = float(record["time"])
        if _similar(current["text"], text) >= similarity_threshold and time - last_time <= frame_interval * 2.25:
            current["end"] = round(time + frame_interval, 3)
            current["confidence_values"].append(float(record.get("confidence") or 0.0))
            current["frames"].append(record.get("frame"))
            if len(text) > len(current["text"]):
                current["text"] = text
        else:
            merged.append(_finalize_event(current))
            current = _new_event(record)
        last_time = time

    merged.append(_finalize_event(current))
    return merged


def _new_event(record: dict) -> dict:
    time = float(record["time"])
    return {
        "start": round(time, 3),
        "end": round(time, 3),
        "type": "subtitle",
        "text": str(record["text"]),
        "source": "ocr",
        "confidence_values": [float(record.get("confidence") or 0.0)],
        "frames": [record.get("frame")],
    }


def _finalize_event(event: dict) -> dict:
    values = event.pop("confidence_values")
    event["confidence"] = round(sum(values) / len(values), 4) if values else 0.0
    return event


def _similar(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return difflib.SequenceMatcher(None, left, right).ratio()
