from __future__ import annotations

from pathlib import Path


def build_timeline(
    video_path: Path,
    duration: float,
    language: str,
    subtitles: list[dict],
    gap_threshold: float = 1.0,
) -> dict:
    events = _insert_gaps(sorted(subtitles, key=lambda item: (item["start"], item["end"])), duration, gap_threshold)
    return {
        "video_info": {
            "duration": round(duration, 3),
            "language": language,
            "title": video_path.name,
            "timeline_source": "ocr_only",
        },
        "events": events,
    }


def _insert_gaps(subtitles: list[dict], duration: float, gap_threshold: float) -> list[dict]:
    events: list[dict] = []
    cursor = 0.0
    for subtitle in subtitles:
        start = float(subtitle["start"])
        end = float(subtitle["end"])
        if start - cursor > gap_threshold:
            events.append(_gap_event(cursor, start))
        events.append(_subtitle_event(subtitle))
        cursor = max(cursor, end)

    if duration - cursor > gap_threshold:
        events.append(_gap_event(cursor, duration))
    return events


def _subtitle_event(subtitle: dict) -> dict:
    return {
        "start": round(float(subtitle["start"]), 3),
        "end": round(float(subtitle["end"]), 3),
        "type": "subtitle",
        "text": subtitle["text"],
        "source": "ocr",
        "confidence": round(float(subtitle.get("confidence") or 0.0), 4),
    }


def _gap_event(start: float, end: float) -> dict:
    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "type": "subtitle_gap",
        "text": "",
        "source": "no_subtitle",
        "confidence": 0.7,
        "emotion": "待 LLM 根据上下文判断",
    }
