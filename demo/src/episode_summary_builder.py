from __future__ import annotations

from typing import Any


def build_episode_summary(
    story_analysis: dict[str, Any],
    previous_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overview = story_analysis.get("overview", {})
    segments = story_analysis.get("segments", [])
    highlights = story_analysis.get("highlights", [])

    main_events = [
        {
            "start": segment.get("start"),
            "end": segment.get("end"),
            "summary": segment.get("summary"),
            "labels": segment.get("labels", []),
        }
        for segment in segments[:6]
    ]
    character_updates = [
        {
            "name": item.get("name"),
            "role": item.get("role"),
            "evidence": item.get("evidence", []),
        }
        for item in overview.get("main_characters", [])
    ]
    relationship_updates = [
        {
            "pair": item.get("pair"),
            "relation": item.get("relation"),
            "evidence": item.get("evidence", []),
        }
        for item in overview.get("relationships", [])
    ]
    ending_hook = ""
    if highlights:
        last_highlight = max(highlights, key=lambda item: float(item.get("end") or 0.0))
        ending_hook = last_highlight.get("title", "") or last_highlight.get("hook", "")
    elif segments:
        ending_hook = segments[-1].get("summary", "")

    open_questions = list(story_analysis.get("uncertainties", []))
    carry_over = _build_carry_over_state(story_analysis, previous_summary)

    return {
        "title": overview.get("title", ""),
        "story_type": overview.get("story_type", ""),
        "core_conflict": overview.get("core_conflict", ""),
        "main_events": main_events,
        "character_updates": character_updates,
        "relationship_updates": relationship_updates,
        "highlight_titles": [item.get("title", "") for item in highlights[:5]],
        "ending_hook": ending_hook,
        "open_questions": open_questions,
        "carry_over_state": carry_over,
    }


def _build_carry_over_state(
    story_analysis: dict[str, Any],
    previous_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    overview = story_analysis.get("overview", {})
    prev_hook = ""
    if previous_summary:
        latest_episode = previous_summary.get("latest_episode", {})
        prev_hook = str(previous_summary.get("ending_hook", "") or latest_episode.get("ending_hook", ""))

    return {
        "relationship_state": _first_relation(overview),
        "core_conflict": overview.get("core_conflict", ""),
        "previous_hook": prev_hook,
        "current_hook": _latest_hook(story_analysis),
    }


def _first_relation(overview: dict[str, Any]) -> str:
    relationships = overview.get("relationships", [])
    if not relationships:
        return ""
    first = relationships[0]
    return f"{first.get('pair', '')}: {first.get('relation', '')}"


def _latest_hook(story_analysis: dict[str, Any]) -> str:
    highlights = story_analysis.get("highlights", [])
    if highlights:
        last_highlight = max(highlights, key=lambda item: float(item.get("end") or 0.0))
        return last_highlight.get("hook", "") or last_highlight.get("title", "")
    segments = story_analysis.get("segments", [])
    return segments[-1].get("summary", "") if segments else ""
