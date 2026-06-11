from __future__ import annotations

from typing import Any


def build_story_segments(
    timeline: dict[str, Any],
    max_segment_duration: float = 24.0,
    split_gap_threshold: float = 2.5,
    max_events_per_segment: int = 6,
) -> list[dict[str, Any]]:
    events = timeline.get("events", [])
    if not events:
        return []

    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for event in events:
        if not current:
            current = [event]
            continue

        current_start = float(current[0]["start"])
        next_end = float(event["end"])
        duration = next_end - current_start
        should_split = (
            _is_large_gap(event, split_gap_threshold)
            or duration > max_segment_duration
            or len(current) >= max_events_per_segment
        )

        if should_split:
            segments.append(current)
            current = [event]
            continue

        current.append(event)

    if current:
        segments.append(current)

    output: list[dict[str, Any]] = []
    for index, segment_events in enumerate(segments, start=1):
        subtitle_events = [event for event in segment_events if event.get("type") == "subtitle"]
        transcript = " ".join(event.get("text", "") for event in subtitle_events if event.get("text"))
        output.append(
            {
                "segment_id": f"segment_{index:03d}",
                "start": round(float(segment_events[0]["start"]), 3),
                "end": round(float(segment_events[-1]["end"]), 3),
                "duration": round(float(segment_events[-1]["end"]) - float(segment_events[0]["start"]), 3),
                "subtitle_count": len(subtitle_events),
                "transcript": transcript,
                "events": [
                    {
                        "start": event.get("start"),
                        "end": event.get("end"),
                        "type": event.get("type"),
                        "text": event.get("text"),
                        "source": event.get("source"),
                        "confidence": event.get("confidence"),
                    }
                    for event in segment_events
                ],
            }
        )
    return output


def _is_large_gap(event: dict[str, Any], threshold: float) -> bool:
    return event.get("type") == "subtitle_gap" and float(event.get("end") or 0.0) - float(event.get("start") or 0.0) >= threshold
