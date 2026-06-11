from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import httpx
from openai import BadRequestError

from .config import Settings
from .prompts import (
    build_clip_suggestions_prompt,
    build_choice_point_prompt,
    build_highlights_prompt,
    build_overview_prompt,
    build_segment_batch_prompt,
    build_series_memory_prompt,
    build_system_prompt,
)


@contextmanager
def _temporary_clear_proxy_env():
    proxy_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    backup = {key: __import__("os").environ.get(key) for key in proxy_keys}
    try:
        for key in proxy_keys:
            __import__("os").environ.pop(key, None)
        yield
    finally:
        for key, value in backup.items():
            if value is not None:
                __import__("os").environ[key] = value


def analyze_story_with_llm(
    timeline: dict[str, Any],
    segments: list[dict[str, Any]],
    previous_memory: dict[str, Any] | None,
    settings: Settings,
    model: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    from openai import OpenAI

    client = _build_client(settings=settings, client_cls=OpenAI)
    selected_model = model or settings.llm_model
    system_prompt = build_system_prompt()

    with _temporary_clear_proxy_env():
        overview_payload = _run_json_task(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=build_overview_prompt(timeline=timeline, previous_memory=previous_memory),
            temperature=temperature,
        )
        overview = overview_payload.get("overview", {})
        uncertainties = overview_payload.get("uncertainties", [])

        analyzed_segments = _analyze_segments_in_batches(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            segments=segments,
            overview=overview,
            temperature=temperature,
        )

        highlights_payload = _run_json_task(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=build_highlights_prompt(
                analyzed_segments=analyzed_segments,
                overview=overview,
            ),
            temperature=temperature,
        )
        highlights = highlights_payload.get("highlights", [])

        clip_payload = _run_json_task(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=build_clip_suggestions_prompt(
                analyzed_segments=analyzed_segments,
                highlights=highlights,
                overview=overview,
            ),
            temperature=temperature,
        )
        clip_suggestions = clip_payload.get("clip_suggestions", [])

    return {
        "overview": overview,
        "segments": analyzed_segments,
        "highlights": highlights,
        "clip_suggestions": clip_suggestions,
        "uncertainties": uncertainties,
    }


def update_series_memory_with_llm(
    previous_memory: dict[str, Any] | None,
    episode_summary: dict[str, Any],
    story_analysis: dict[str, Any],
    settings: Settings,
    model: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    from openai import OpenAI

    client = _build_client(settings=settings, client_cls=OpenAI)
    selected_model = model or settings.llm_model
    system_prompt = build_system_prompt()

    with _temporary_clear_proxy_env():
        payload = _run_json_task(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=build_series_memory_prompt(
                previous_memory=previous_memory,
                episode_summary=episode_summary,
                story_analysis=_compact_story_analysis_for_memory(story_analysis),
            ),
            temperature=temperature,
        )
    return payload.get("series_memory", payload)


def generate_choice_point_with_llm(
    candidates: list[dict[str, Any]],
    overview: dict[str, Any],
    episode_summary: dict[str, Any] | None,
    settings: Settings,
    model: str | None = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    from openai import OpenAI

    client = _build_client(settings=settings, client_cls=OpenAI)
    selected_model = model or settings.llm_model
    system_prompt = build_system_prompt()

    with _temporary_clear_proxy_env():
        return _run_json_task(
            client=client,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=build_choice_point_prompt(
                candidates=candidates,
                overview=overview,
                episode_summary=episode_summary,
            ),
            temperature=temperature,
        )


def _analyze_segments_in_batches(
    client: Any,
    model: str,
    system_prompt: str,
    segments: list[dict[str, Any]],
    overview: dict[str, Any],
    temperature: float,
    batch_size: int = 4,
) -> list[dict[str, Any]]:
    analyzed: list[dict[str, Any]] = []
    for index in range(0, len(segments), batch_size):
        batch = segments[index : index + batch_size]
        payload = _run_json_task(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=build_segment_batch_prompt(segment_batch=batch, overview=overview),
            temperature=temperature,
        )
        analyzed.extend(payload.get("segments", []))

    order = {segment.get("segment_id"): position for position, segment in enumerate(segments)}
    analyzed.sort(key=lambda item: order.get(item.get("segment_id"), 10**9))
    return analyzed


def _compact_story_analysis_for_memory(story_analysis: dict[str, Any]) -> dict[str, Any]:
    highlights = story_analysis.get("highlights", [])
    highlight_windows = [
        (
            float(item.get("start") or 0.0),
            float(item.get("end") or item.get("start") or 0.0),
        )
        for item in highlights
        if isinstance(item, dict)
    ]
    key_segments = []
    for segment in story_analysis.get("segments", []):
        if not isinstance(segment, dict):
            continue
        labels = [str(item) for item in segment.get("labels", [])]
        start = float(segment.get("start") or 0.0)
        end = float(segment.get("end") or start)
        near_highlight = any(start <= h_end + 3 and end >= h_start - 3 for h_start, h_end in highlight_windows)
        important_label = bool(set(labels) & {"conflict", "reversal", "suspense", "face_slap", "setup"})
        if near_highlight or important_label:
            key_segments.append(
                {
                    "segment_id": segment.get("segment_id"),
                    "start": start,
                    "end": end,
                    "summary": _clip_text(segment.get("summary"), 120),
                    "function": _clip_text(segment.get("function"), 80),
                    "labels": labels[:4],
                    "evidence": _clip_list(segment.get("evidence"), max_items=2, max_chars=80),
                }
            )
        if len(key_segments) >= 8:
            break

    return {
        "overview": story_analysis.get("overview", {}),
        "highlights": [_compact_highlight(item) for item in highlights[:5] if isinstance(item, dict)],
        "clip_suggestions": [
            _compact_clip(item)
            for item in story_analysis.get("clip_suggestions", [])[:3]
            if isinstance(item, dict)
        ],
        "key_segments": key_segments,
        "uncertainties": _clip_list(story_analysis.get("uncertainties"), max_items=4, max_chars=80),
    }


def _compact_highlight(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": _clip_text(item.get("title"), 80),
        "start": item.get("start"),
        "end": item.get("end"),
        "type": _clip_text(item.get("type"), 40),
        "reason": _clip_text(item.get("reason"), 140),
        "emotion_value": _clip_text(item.get("emotion_value"), 80),
        "hook": _clip_text(item.get("hook"), 100),
        "evidence": _clip_list(item.get("evidence"), max_items=2, max_chars=80),
    }


def _compact_clip(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": item.get("start"),
        "end": item.get("end"),
        "title": _clip_text(item.get("title"), 80),
        "opening_hook": _clip_text(item.get("opening_hook"), 100),
        "ending_bang": _clip_text(item.get("ending_bang"), 100),
        "reason": _clip_text(item.get("reason"), 120),
    }


def _clip_list(value: Any, max_items: int, max_chars: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = _clip_text(item, max_chars)
        if text:
            result.append(text)
        if len(result) >= max_items:
            break
    return result


def _clip_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _run_json_task(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> dict[str, Any]:
    response = _create_chat_completion(
        client=client,
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        prefer_json_object=True,
    )
    content = response.choices[0].message.content or "{}"
    try:
        return _parse_json_payload(content)
    except RuntimeError:
        repaired = _repair_json_with_llm(client=client, raw_content=content, model=model)
        return _parse_json_payload(repaired)


def _build_client(settings: Settings, client_cls: Any) -> Any:
    http_client = httpx.Client(trust_env=False)
    provider = settings.llm_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or use --skip-llm.")
        return client_cls(api_key=settings.openai_api_key, http_client=http_client)
    if provider in {"ark", "doubao", "volcengine"}:
        if not settings.ark_api_key:
            raise RuntimeError("ARK_API_KEY is not set. Add it to .env or use --skip-llm.")
        return client_cls(
            api_key=settings.ark_api_key,
            base_url=settings.ark_base_url,
            http_client=http_client,
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def _parse_json_payload(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM did not return valid JSON.\nRaw output:\n{content}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("LLM JSON payload must be an object.")
    return payload


def _repair_json_with_llm(client: Any, raw_content: str, model: str) -> str:
    repair_prompt = f"""下面这段内容本来应该是一个 JSON 对象，但目前不是合法 JSON。

请你只做一件事：在不改变原始语义的前提下，把它修复成合法 JSON。

要求：
1. 只输出合法 JSON
2. 不要输出 Markdown 代码块
3. 不要补充原文没有的新剧情
4. 如果原文中有明显截断或缺失，就尽量保留已有字段并让 JSON 合法

原始内容：
{raw_content}
"""
    response = _create_chat_completion(
        client=client,
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "你是一个 JSON 修复器，只输出合法 JSON。"},
            {"role": "user", "content": repair_prompt},
        ],
        prefer_json_object=True,
    )
    return response.choices[0].message.content or "{}"


def _create_chat_completion(
    client: Any,
    model: str,
    temperature: float,
    messages: list[dict[str, str]],
    prefer_json_object: bool,
) -> Any:
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if prefer_json_object:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError:
        if not prefer_json_object:
            raise
        kwargs.pop("response_format", None)
        return client.chat.completions.create(**kwargs)
