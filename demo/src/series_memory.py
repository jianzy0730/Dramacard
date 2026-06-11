from __future__ import annotations

from typing import Any


def compact_series_memory(memory: dict[str, Any]) -> dict[str, Any]:
    latest_episode = _dict_value(memory.get("latest_episode"))
    return {
        "episodes_covered": _clip_scalar(memory.get("episodes_covered"), 40),
        "previous_story": _clip_scalar(
            memory.get("previous_story") or memory.get("series_summary"),
            300,
        ),
        "current_situation": _clip_scalar(
            memory.get("current_situation") or memory.get("current_state"),
            160,
        ),
        "character_notes": _compact_notes(
            memory.get("character_notes") or _legacy_character_notes(memory),
            max_items=6,
            max_chars=70,
        ),
        "relationship_notes": _compact_notes(
            memory.get("relationship_notes") or _legacy_relationship_notes(memory),
            max_items=6,
            max_chars=80,
        ),
        "unresolved_hooks": _compact_notes(
            memory.get("unresolved_hooks") or _legacy_unresolved_hooks(memory),
            max_items=6,
            max_chars=80,
        ),
        "latest_episode": {
            "title": _clip_scalar(latest_episode.get("title"), 80),
            "summary": _clip_scalar(latest_episode.get("summary"), 100),
            "ending_hook": _clip_scalar(latest_episode.get("ending_hook"), 90),
        },
    }


def _legacy_character_notes(memory: dict[str, Any]) -> list[str]:
    notes = []
    for item in _list_value(memory.get("main_characters")):
        if not isinstance(item, dict):
            continue
        text = "：".join(
            part
            for part in [
                _clip_scalar(item.get("name"), 24),
                _clip_scalar(item.get("state") or item.get("role"), 90),
            ]
            if part
        )
        if text:
            notes.append(text)
    return notes


def _legacy_relationship_notes(memory: dict[str, Any]) -> list[str]:
    notes = []
    for item in _list_value(memory.get("relationships")):
        if not isinstance(item, dict):
            continue
        pair = _clip_scalar(item.get("pair"), 40)
        state = _clip_scalar(item.get("state") or item.get("relation"), 80)
        change = _clip_scalar(item.get("change"), 80)
        text = f"{pair}：{state}" if pair and state else pair or state
        if change:
            text = f"{text}，{change}" if text else change
        if text:
            notes.append(text)
    return notes


def _legacy_unresolved_hooks(memory: dict[str, Any]) -> list[str]:
    notes = []
    for key in ("open_threads", "foreshadowing"):
        for item in _list_value(memory.get(key)):
            if not isinstance(item, dict):
                continue
            text = item.get("title") or item.get("hint") or item.get("last_update")
            text = _clip_scalar(text, 120)
            if text:
                notes.append(text)
    return notes


def _compact_notes(value: Any, max_items: int, max_chars: int) -> list[str]:
    notes = []
    for item in _list_value(value):
        if isinstance(item, dict):
            text = item.get("summary") or item.get("title") or item.get("state") or item.get("hint")
        else:
            text = item
        text = _clip_scalar(text, max_chars)
        if text and text not in notes:
            notes.append(text)
        if len(notes) >= max_items:
            break
    return notes


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clip_scalar(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
