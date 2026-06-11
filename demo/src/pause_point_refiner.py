from __future__ import annotations

from typing import Any


def enrich_story_analysis_with_pause_points(
    story_analysis: dict[str, Any],
    timeline: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(story_analysis)
    events = timeline.get("events", [])
    duration = float(timeline.get("video_info", {}).get("duration") or 0.0)

    enriched["highlights"] = [
        _add_pause_fields(item, events=events, duration=duration)
        for item in story_analysis.get("highlights", [])
    ]
    enriched["clip_suggestions"] = [
        _add_pause_fields(item, events=events, duration=duration)
        for item in story_analysis.get("clip_suggestions", [])
    ]
    return enriched


def _add_pause_fields(item: dict[str, Any], events: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    enriched = dict(item)
    start = float(item.get("start") or 0.0)
    end = float(item.get("end") or start)
    subtitle_events = _find_subtitle_events(events, start=start, end=end)

    if subtitle_events:
        anchor = float(subtitle_events[-1]["end"])
        cue_duration = max(0.15, min(0.35, (float(subtitle_events[-1]["end"]) - float(subtitle_events[-1]["start"])) * 0.4))
        trigger_at = max(start, anchor - cue_duration)
        pause_at = min(duration or end, anchor + 0.12)
    else:
        trigger_at = max(start, end - 0.25)
        pause_at = min(duration or end, end + 0.12)

    enriched["trigger_at"] = round(trigger_at, 3)
    enriched["pause_at"] = round(max(enriched["trigger_at"], pause_at), 3)
    return enriched


def _find_subtitle_events(events: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    matched = []
    for event in events:
        if event.get("type") != "subtitle":
            continue
        event_start = float(event.get("start") or 0.0)
        event_end = float(event.get("end") or event_start)
        if event_end < start or event_start > end:
            continue
        matched.append(event)
    matched.sort(key=lambda event: float(event.get("end") or 0.0))
    return matched
