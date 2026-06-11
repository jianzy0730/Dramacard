from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import load_json, save_json
from .video_utils import extract_frame_at_timestamp, get_video_duration


def build_drama_highlight_report(
    drama_output_dir: Path,
    drama_video_dir: Path,
    output_dir: Path,
    max_highlights: int | None = None,
    min_episode_gap: int = 2,
    per_episode_limit: int = 1,
    min_score: int = 72,
) -> dict[str, Any]:
    drama_output_dir = drama_output_dir.resolve()
    drama_video_dir = drama_video_dir.resolve()
    output_dir = output_dir.resolve()
    if not drama_output_dir.exists():
        raise FileNotFoundError(f"Drama output directory not found: {drama_output_dir}")
    if not drama_video_dir.exists():
        raise FileNotFoundError(f"Drama video directory not found: {drama_video_dir}")

    episode_dirs = sorted(
        [path for path in drama_output_dir.iterdir() if path.is_dir()],
        key=_episode_dir_sort_key,
    )
    episode_payloads: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for episode_dir in episode_dirs:
        story_analysis_path = episode_dir / "story_analysis.json"
        episode_summary_path = episode_dir / "episode_summary.json"
        if not story_analysis_path.exists():
            continue

        story_analysis = load_json(story_analysis_path)
        episode_summary = load_json(episode_summary_path) if episode_summary_path.exists() else {}
        episode_name = episode_dir.name
        episode_number = _extract_episode_number(episode_name)
        episode_payloads.append(
            {
                "episode_name": episode_name,
                "episode_number": episode_number,
                "story_analysis": story_analysis,
                "episode_summary": episode_summary,
            }
        )

        for index, highlight in enumerate(story_analysis.get("highlights", []), start=1):
            candidate = _build_highlight_candidate(
                drama_name=drama_output_dir.name,
                episode_name=episode_name,
                episode_number=episode_number,
                highlight_index=index,
                highlight=highlight,
                episode_summary=episode_summary,
                clip_suggestions=story_analysis.get("clip_suggestions", []),
            )
            candidates.append(candidate)

    resolved_max_highlights = max_highlights or _default_max_highlights(len(episode_dirs))
    selected = _select_highlights(
        candidates,
        max_highlights=resolved_max_highlights,
        min_episode_gap=min_episode_gap,
        per_episode_limit=per_episode_limit,
        min_score=min_score,
    )

    character_catalog = _build_character_catalog(episode_payloads)
    materialized_character_refs = _materialize_character_reference_frames(
        character_catalog=character_catalog,
        drama_video_dir=drama_video_dir,
        output_dir=output_dir / "character_refs",
    )

    keyframes_dir = output_dir / "keyframes"
    candidate_frames_dir = output_dir / "candidate_frames"
    for item in selected:
        video_path = _resolve_episode_video_path(drama_video_dir, str(item["episode_name"]))
        if video_path is None:
            item["keyframe_path"] = ""
            item["candidate_frames"] = []
            item["visible_characters"] = []
            item["card_mode"] = "story_card"
            item["image_generation_prompt"] = _build_image_generation_prompt(
                item=item,
                character_refs=[],
                card_mode="story_card",
            )
            item["generation_assets"] = {
                "scene_reference_paths": [],
                "character_reference_ids": [],
                "character_reference_paths": [],
                "visibility_source": "story_text_inference",
                "ready_for_image_generation": False,
            }
            continue

        candidate_frames = _extract_highlight_candidate_frames(
            item=item,
            video_path=video_path,
            output_dir=candidate_frames_dir,
        )
        item["candidate_frames"] = candidate_frames
        keyframe_path = _materialize_primary_keyframe(
            item=item,
            video_path=video_path,
            output_dir=keyframes_dir,
        )
        item["keyframe_path"] = str(keyframe_path) if keyframe_path else ""

        visible_characters = _infer_visible_characters(item=item, character_refs=materialized_character_refs)
        card_mode = _select_card_mode(item=item, visible_characters=visible_characters)
        character_refs = _select_character_refs_for_highlight(
            visible_characters=visible_characters,
            character_refs=materialized_character_refs,
        )
        item["visible_characters"] = visible_characters
        item["card_mode"] = card_mode
        item["image_generation_prompt"] = _build_image_generation_prompt(
            item=item,
            character_refs=character_refs,
            card_mode=card_mode,
        )
        item["generation_assets"] = {
            "scene_reference_paths": [frame["path"] for frame in candidate_frames[:4]],
            "character_reference_ids": [ref["character_id"] for ref in character_refs],
            "character_reference_paths": [
                frame["path"]
                for ref in character_refs
                for frame in ref.get("reference_frames", [])[:2]
            ],
            "visibility_source": "story_text_inference",
            "ready_for_image_generation": bool(candidate_frames) and bool(character_refs),
        }

    report = {
        "drama_title": drama_output_dir.name,
        "episode_count": len(episode_dirs),
        "highlight_count": len(selected),
        "selection_policy": {
            "max_highlights": resolved_max_highlights,
            "min_episode_gap": min_episode_gap,
            "per_episode_limit": per_episode_limit,
            "min_score": min_score,
        },
        "character_refs": materialized_character_refs,
        "generation_notes": [
            "visible_characters 基于剧情文本和人物信息推断，不是视觉识别结果。",
            "scene_card 适合主角在高光时段较明确出现的卡面；story_card 适合空镜、电话、背影或主角缺席的叙事型卡面。",
            "candidate_frames 用于给图像生成模型提供场景参考；character_refs 用于稳定人物外观一致性。",
        ],
        "highlights": selected,
    }
    save_json(report, output_dir / "drama_highlight_report.json")
    return report


def _build_highlight_candidate(
    drama_name: str,
    episode_name: str,
    episode_number: int,
    highlight_index: int,
    highlight: dict[str, Any],
    episode_summary: dict[str, Any],
    clip_suggestions: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(highlight.get("title", "")).strip()
    highlight_type = str(highlight.get("type", "")).strip()
    reason = str(highlight.get("reason", "")).strip()
    hook = str(highlight.get("hook", "")).strip()
    emotion_value = str(highlight.get("emotion_value", "")).strip()
    evidence = list(highlight.get("evidence", []))
    start = float(highlight.get("start") or 0.0)
    end = float(highlight.get("end") or start)
    trigger_at = float(highlight.get("trigger_at") or max(start, end - 0.25))
    pause_at = float(highlight.get("pause_at") or end)
    keyframe_time = pause_at or end or start

    score = _score_highlight(
        title=title,
        highlight_type=highlight_type,
        reason=reason,
        hook=hook,
        emotion_value=emotion_value,
        episode_summary=episode_summary,
        clip_suggestions=clip_suggestions,
        start=start,
        end=end,
    )
    star_level = _score_to_star_level(score)
    card_prompt = _build_card_prompt(
        drama_name=drama_name,
        episode_name=episode_name,
        star_level=star_level,
        title=title,
        highlight_type=highlight_type,
        reason=reason,
        emotion_value=emotion_value,
        evidence=evidence,
    )

    return {
        "highlight_id": f"h{episode_number:03d}_{highlight_index:02d}",
        "episode_name": episode_name,
        "episode_number": episode_number,
        "title": title,
        "highlight_type": highlight_type,
        "score": score,
        "star_level": star_level,
        "start": round(start, 3),
        "end": round(end, 3),
        "trigger_at": round(trigger_at, 3),
        "pause_at": round(pause_at, 3),
        "keyframe_time": round(keyframe_time, 3),
        "core_content": reason or title,
        "emotion_value": emotion_value,
        "hook": hook,
        "evidence": evidence,
        "card_prompt": card_prompt,
        "keyframe_path": "",
    }


def _build_character_catalog(episode_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for payload in episode_payloads:
        overview = payload["story_analysis"].get("overview", {})
        for character in overview.get("main_characters", []):
            name = str(character.get("name", "")).strip()
            if not name:
                continue
            entry = catalog.setdefault(
                name,
                {
                    "character_id": _slugify(name),
                    "name": name,
                    "role": str(character.get("role", "")).strip(),
                    "confidence": 0.0,
                    "mentions": 0,
                    "evidence": [],
                    "keywords": set(),
                    "reference_candidates": [],
                },
            )
            entry["mentions"] += 1
            entry["confidence"] = max(float(character.get("confidence") or 0.0), float(entry["confidence"]))
            if not entry["role"]:
                entry["role"] = str(character.get("role", "")).strip()
            entry["evidence"].extend(str(item) for item in character.get("evidence", []) if item)
            entry["keywords"].update(_character_keywords(name=name, role=str(character.get("role", "")).strip()))

    for payload in episode_payloads:
        episode_name = str(payload["episode_name"])
        episode_number = int(payload["episode_number"])
        story_analysis = payload["story_analysis"]
        highlight_candidates = list(story_analysis.get("highlights", []))
        segment_candidates = list(story_analysis.get("segments", []))
        for entry in catalog.values():
            for index, highlight in enumerate(highlight_candidates, start=1):
                text = _highlight_text_blob(highlight)
                score = _keyword_overlap_score(text, entry["keywords"])
                if score <= 0:
                    continue
                entry["reference_candidates"].append(
                    {
                        "source_type": "highlight",
                        "episode_name": episode_name,
                        "episode_number": episode_number,
                        "timestamp": float(highlight.get("pause_at") or highlight.get("end") or highlight.get("start") or 0.0),
                        "score": score + 6,
                        "reason": f"highlight_{index}",
                    }
                )
            for segment in segment_candidates:
                text = _segment_text_blob(segment)
                score = _keyword_overlap_score(text, entry["keywords"])
                if score <= 0:
                    continue
                start = float(segment.get("start") or 0.0)
                end = float(segment.get("end") or start)
                entry["reference_candidates"].append(
                    {
                        "source_type": "segment",
                        "episode_name": episode_name,
                        "episode_number": episode_number,
                        "timestamp": (start + end) / 2,
                        "score": score,
                        "reason": str(segment.get("segment_id") or "segment"),
                    }
                )

    sorted_entries = sorted(
        catalog.values(),
        key=lambda item: (-int(item["mentions"]), -float(item["confidence"]), item["name"]),
    )
    return sorted_entries[:6]


def _materialize_character_reference_frames(
    character_catalog: list[dict[str, Any]],
    drama_video_dir: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for entry in character_catalog:
        sorted_candidates = sorted(
            entry.get("reference_candidates", []),
            key=lambda item: (-int(item["score"]), int(item["episode_number"]), float(item["timestamp"])),
        )
        reference_frames: list[dict[str, Any]] = []
        seen_slots: set[tuple[str, int]] = set()
        for candidate in sorted_candidates:
            if len(reference_frames) >= 3:
                break
            episode_name = str(candidate["episode_name"])
            time_bucket = int(float(candidate["timestamp"]) * 2)
            dedupe_key = (episode_name, time_bucket)
            if dedupe_key in seen_slots:
                continue
            video_path = _resolve_episode_video_path(drama_video_dir, episode_name)
            if video_path is None:
                continue
            filename = f"{entry['character_id']}_{episode_name}_{len(reference_frames) + 1:02d}.jpg"
            frame_path = output_dir / entry["character_id"] / filename
            extract_frame_at_timestamp(video_path, frame_path, float(candidate["timestamp"]))
            reference_frames.append(
                {
                    "episode_name": episode_name,
                    "episode_number": int(candidate["episode_number"]),
                    "timestamp": round(float(candidate["timestamp"]), 3),
                    "path": str(frame_path),
                    "source_type": str(candidate["source_type"]),
                    "source_ref": str(candidate["reason"]),
                }
            )
            seen_slots.add(dedupe_key)

        materialized.append(
            {
                "character_id": entry["character_id"],
                "name": entry["name"],
                "role": entry["role"],
                "confidence": round(float(entry["confidence"]), 3),
                "mentions": int(entry["mentions"]),
                "keywords": sorted(entry["keywords"]),
                "evidence": list(dict.fromkeys(entry["evidence"]))[:5],
                "reference_frames": reference_frames,
            }
        )
    return materialized


def _materialize_primary_keyframe(item: dict[str, Any], video_path: Path, output_dir: Path) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    keyframe_filename = f"ep{int(item['episode_number']):03d}_{item['highlight_id']}.jpg"
    keyframe_path = output_dir / keyframe_filename
    extract_frame_at_timestamp(video_path, keyframe_path, float(item["keyframe_time"]))
    return keyframe_path


def _extract_highlight_candidate_frames(
    item: dict[str, Any],
    video_path: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    duration = get_video_duration(video_path)
    start = float(item.get("start") or 0.0)
    end = float(item.get("end") or start)
    trigger_at = float(item.get("trigger_at") or end)
    pause_at = float(item.get("pause_at") or end)
    midpoint = (start + end) / 2
    timestamps = [
        ("pre_trigger", max(0.0, trigger_at - 0.6)),
        ("trigger", trigger_at),
        ("midpoint", midpoint),
        ("pause", pause_at),
        ("post_pause", min(duration, pause_at + 0.6)),
    ]
    extracted: list[dict[str, Any]] = []
    seen_buckets: set[int] = set()
    for label, timestamp in timestamps:
        bucket = int(timestamp * 4)
        if bucket in seen_buckets:
            continue
        filename = f"{item['highlight_id']}_{label}.jpg"
        output_path = output_dir / f"ep{int(item['episode_number']):03d}" / filename
        extract_frame_at_timestamp(video_path, output_path, timestamp)
        extracted.append(
            {
                "label": label,
                "timestamp": round(timestamp, 3),
                "path": str(output_path),
            }
        )
        seen_buckets.add(bucket)
    return extracted


def _infer_visible_characters(
    item: dict[str, Any],
    character_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    highlight_text = _highlight_text_blob(item)
    matched: list[dict[str, Any]] = []
    for ref in character_refs:
        overlap_score = _keyword_overlap_score(highlight_text, set(ref.get("keywords", [])))
        if overlap_score <= 0:
            continue
        matched.append(
            {
                "character_id": ref["character_id"],
                "name": ref["name"],
                "role": ref.get("role", ""),
                "match_score": overlap_score,
            }
        )
    matched.sort(key=lambda item: (-int(item["match_score"]), item["name"]))
    return matched[:3]


def _select_card_mode(item: dict[str, Any], visible_characters: list[dict[str, Any]]) -> str:
    text = _highlight_text_blob(item)
    if not visible_characters:
        return "story_card"
    if any(keyword in text for keyword in ["电话", "声音", "回忆", "梦", "噩梦", "空镜", "门外", "车外"]):
        return "story_card"
    return "scene_card"


def _select_character_refs_for_highlight(
    visible_characters: list[dict[str, Any]],
    character_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted_ids = {item["character_id"] for item in visible_characters}
    return [ref for ref in character_refs if ref["character_id"] in wanted_ids]


def _build_image_generation_prompt(
    item: dict[str, Any],
    character_refs: list[dict[str, Any]],
    card_mode: str,
) -> str:
    visible_names = "、".join(ref["name"] for ref in character_refs) or "主角群"
    reference_clause = (
        f"严格参考角色素材中的人物外观，保持 {visible_names} 的脸型、发型、年龄感和气质一致。"
        if character_refs
        else "优先表现剧情事件和情绪张力，不要强行捏造未出现的人物近景。"
    )
    mode_clause = (
        "以高光发生当刻的镜头冲突为主体，强调人物动作关系和戏剧张力。"
        if card_mode == "scene_card"
        else "以叙事型剧情卡呈现事件，不强求还原单一镜头，可用象征性构图表达关系与反转。"
    )
    evidence_text = "；".join(str(item) for item in item.get("evidence", [])[:3] if item)
    return (
        f"为短剧高光生成一张 {card_mode} 风格的三星彩剧情卡。"
        f"剧情标题：{item.get('title', '')}。高光类型：{item.get('highlight_type', '')}。"
        f"核心内容：{item.get('core_content', '')}。情绪价值：{item.get('emotion_value', '')}。"
        f"关键台词：{evidence_text}。{mode_clause}{reference_clause}"
        "画面风格：高冲击感、影视感光影、游戏抽卡质感、适合暂停弹出展示。"
    )


def _score_highlight(
    title: str,
    highlight_type: str,
    reason: str,
    hook: str,
    emotion_value: str,
    episode_summary: dict[str, Any],
    clip_suggestions: list[dict[str, Any]],
    start: float,
    end: float,
) -> int:
    score = 50
    type_text = f"{title} {highlight_type} {reason} {hook} {emotion_value}"
    strong_words = ["名场面", "反转", "爆点", "反杀", "打脸", "高光", "真相", "求婚", "离婚", "表白", "生死", "转折", "爽点"]
    medium_words = ["冲突", "甜", "悬念", "危机", "对峙", "逆转", "告白", "误会", "身份", "钩子"]
    pivot_words = [
        "离婚",
        "回归",
        "真相",
        "身份",
        "曝光",
        "揭穿",
        "反转",
        "逆转",
        "决定",
        "选择",
        "求婚",
        "分手",
        "结婚",
        "白月光",
        "出轨",
        "原配",
        "小三",
        "救命",
        "生死",
        "入行",
        "回家",
        "重逢",
        "误会",
        "摊牌",
    ]
    relation_change_words = [
        "老公",
        "老婆",
        "离婚",
        "结婚",
        "表白",
        "分手",
        "回归",
        "白月光",
        "原配",
        "小三",
        "偷情",
        "复婚",
        "摊牌",
    ]

    score += 14 * sum(1 for word in strong_words if word in type_text)
    score += 7 * sum(1 for word in medium_words if word in type_text)
    score += 12 * sum(1 for word in pivot_words if word in type_text)
    score += 8 * sum(1 for word in relation_change_words if word in type_text)

    if "适合" in hook or "钩子" in hook:
        score += 10
    if "非常适合" in hook:
        score += 8
    if len(emotion_value) >= 18:
        score += 6
    if len(reason) >= 24:
        score += 6
    if end - start >= 8:
        score += 4

    ending_hook = str(episode_summary.get("ending_hook", ""))
    if title and title in ending_hook:
        score += 12
    if _is_pivot_hook(ending_hook, title=title, reason=reason, hook=hook):
        score += 18
    if any(_clip_overlaps(start, end, clip) for clip in clip_suggestions):
        score += 8

    return min(score, 100)


def _score_to_star_level(score: int) -> int:
    if score >= 85:
        return 3
    if score >= 68:
        return 2
    return 1


def _clip_overlaps(start: float, end: float, clip: dict[str, Any]) -> bool:
    clip_start = float(clip.get("start") or 0.0)
    clip_end = float(clip.get("end") or clip_start)
    return not (clip_end < start or clip_start > end)


def _build_card_prompt(
    drama_name: str,
    episode_name: str,
    star_level: int,
    title: str,
    highlight_type: str,
    reason: str,
    emotion_value: str,
    evidence: list[Any],
) -> str:
    evidence_text = "；".join(str(item) for item in evidence[:3] if item)
    return (
        f"为短剧《{drama_name}》{episode_name}生成一张高光剧情卡牌。"
        f"卡牌主题：{title}。高光类型：{highlight_type}。"
        f"星级：{star_level}星。核心剧情：{reason}。情绪价值：{emotion_value}。"
        f"关键台词/依据：{evidence_text}。"
        "风格要求：高冲击感、动态成就感、游戏抽卡视觉、适合视频剧情卡牌收藏。"
    )


def _is_pivot_hook(ending_hook: str, title: str, reason: str, hook: str) -> bool:
    if not ending_hook:
        return False
    text = f"{ending_hook} {title} {reason} {hook}"
    pivot_signals = [
        "转折",
        "真相",
        "身份",
        "回归",
        "白月光",
        "离婚",
        "分手",
        "结婚",
        "曝光",
        "揭穿",
        "摊牌",
        "决定",
        "入行",
        "危机",
        "救命",
        "重逢",
    ]
    return any(word in text for word in pivot_signals)


def _select_highlights(
    candidates: list[dict[str, Any]],
    max_highlights: int,
    min_episode_gap: int,
    per_episode_limit: int,
    min_score: int,
) -> list[dict[str, Any]]:
    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            -_pivot_priority(item),
            -int(item["score"]),
            int(item["episode_number"]),
            float(item["start"]),
        ),
    )
    selected: list[dict[str, Any]] = []
    episode_counts: dict[int, int] = {}
    for candidate in sorted_candidates:
        if len(selected) >= max_highlights:
            break
        if int(candidate["score"]) < min_score:
            continue
        if episode_counts.get(int(candidate["episode_number"]), 0) >= per_episode_limit:
            continue
        if any(_same_episode_overlap(candidate, existing) for existing in selected):
            continue
        if any(_episode_gap_conflict(candidate, existing, min_episode_gap=min_episode_gap) for existing in selected):
            continue
        selected.append(candidate)
        episode_counts[int(candidate["episode_number"])] = episode_counts.get(int(candidate["episode_number"]), 0) + 1
    selected.sort(key=lambda item: (int(item["episode_number"]), float(item["start"])))
    return selected


def _same_episode_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["episode_number"] != right["episode_number"]:
        return False
    left_start, left_end = float(left["start"]), float(left["end"])
    right_start, right_end = float(right["start"]), float(right["end"])
    overlap = max(0.0, min(left_end, right_end) - max(left_start, right_start))
    shorter = max(0.001, min(left_end - left_start, right_end - right_start))
    return overlap / shorter >= 0.55


def _episode_gap_conflict(left: dict[str, Any], right: dict[str, Any], min_episode_gap: int) -> bool:
    return abs(int(left["episode_number"]) - int(right["episode_number"])) < min_episode_gap


def _default_max_highlights(episode_count: int) -> int:
    if episode_count <= 3:
        return 1
    return max(2, episode_count // 3)


def _pivot_priority(item: dict[str, Any]) -> int:
    text = f"{item.get('title', '')} {item.get('highlight_type', '')} {item.get('core_content', '')} {item.get('hook', '')}"
    primary = [
        "离婚",
        "回归",
        "真相",
        "身份",
        "曝光",
        "揭穿",
        "白月光",
        "分手",
        "结婚",
        "摊牌",
        "重逢",
        "生死",
        "入行",
        "反转",
        "逆转",
    ]
    secondary = [
        "冲突",
        "危机",
        "误会",
        "告白",
        "原配",
        "小三",
        "偷情",
        "救命",
        "转折",
    ]
    score = 0
    score += 20 * sum(1 for word in primary if word in text)
    score += 8 * sum(1 for word in secondary if word in text)
    return score


def _character_keywords(name: str, role: str) -> set[str]:
    keywords = set(_extract_chinese_tokens(name))
    keywords.update(token for token in _extract_chinese_tokens(role) if len(token) >= 2)
    keywords.add(name)
    if role:
        keywords.add(role)
    return {token for token in keywords if token}


def _highlight_text_blob(highlight: dict[str, Any]) -> str:
    return " ".join(
        [
            str(highlight.get("title", "")),
            str(highlight.get("highlight_type", highlight.get("type", ""))),
            str(highlight.get("core_content", highlight.get("reason", ""))),
            str(highlight.get("emotion_value", "")),
            str(highlight.get("hook", "")),
            " ".join(str(item) for item in highlight.get("evidence", [])),
        ]
    )


def _segment_text_blob(segment: dict[str, Any]) -> str:
    return " ".join(
        [
            str(segment.get("summary", "")),
            str(segment.get("speaker_guess", "")),
            str(segment.get("function", "")),
            " ".join(str(item) for item in segment.get("labels", [])),
            " ".join(str(item) for item in segment.get("evidence", [])),
        ]
    )


def _keyword_overlap_score(text: str, keywords: set[str]) -> int:
    score = 0
    for token in keywords:
        if token and token in text:
            score += max(1, min(4, len(token) // 2))
    return score


def _extract_chinese_tokens(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]{2,}", text)


def _slugify(text: str) -> str:
    tokens = _extract_chinese_tokens(text)
    if tokens:
        return "_".join(tokens[:3])
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return ascii_text or "character"


def _resolve_episode_video_path(drama_video_dir: Path, episode_name: str) -> Path | None:
    for suffix in [".mp4", ".mov", ".mkv"]:
        candidate = drama_video_dir / f"{episode_name}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _episode_dir_sort_key(path: Path) -> tuple[int, str]:
    return (_extract_episode_number(path.name), path.name)


def _extract_episode_number(name: str) -> int:
    match = re.search(r"(\d+)", name)
    return int(match.group(1)) if match else 0
