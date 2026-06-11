from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import Settings
from .io_utils import load_json, save_json
from .llm_client import generate_choice_point_with_llm


def build_episode_choice_point(
    timeline: dict[str, Any],
    story_analysis: dict[str, Any],
    episode_summary: dict[str, Any] | None,
    settings: Settings,
    model: str | None = None,
) -> dict[str, Any]:
    candidates = _build_choice_candidates(timeline=timeline, story_analysis=story_analysis, episode_summary=episode_summary)
    if not candidates:
        return {
            "episode_title": timeline.get("video_info", {}).get("title", ""),
            "choice_point": None,
            "generation_notes": ["未找到适合插入单次选择互动的剧情转折点。"],
        }

    overview = story_analysis.get("overview", {})
    notes: list[str] = []
    try:
        payload = generate_choice_point_with_llm(
            candidates=candidates[:6],
            overview=overview,
            episode_summary=episode_summary,
            settings=settings,
            model=model,
        )
        choice_point = _normalize_choice_point(payload=payload, candidates=candidates)
    except Exception as exc:
        payload = {}
        choice_point = None
        notes.append(f"LLM 选择点生成失败，已回退到本地规则：{exc}")
    if choice_point is None:
        choice_point = _build_fallback_choice_point(candidates[0])
        notes.append("当前结果使用本地规则兜底生成。")

    return {
        "episode_title": overview.get("title") or timeline.get("video_info", {}).get("title", ""),
        "choice_point": choice_point,
        "generation_notes": [
            "选择点只保留 1 个，适用于一次性漫画插入或单次互动分支。",
            "非原剧情分支会在短篇替代结局后结束，不继续影响后续正片主线。",
            *notes,
        ],
    }


def build_drama_choice_points(
    drama_output_dir: Path,
    settings: Settings,
    model: str | None = None,
) -> dict[str, Any]:
    drama_output_dir = drama_output_dir.resolve()
    if not drama_output_dir.exists():
        raise FileNotFoundError(f"Drama output directory not found: {drama_output_dir}")

    episode_dirs = sorted([path for path in drama_output_dir.iterdir() if path.is_dir()], key=_episode_sort_key)
    episodes: list[dict[str, Any]] = []
    for episode_dir in episode_dirs:
        timeline_path = episode_dir / "timeline.json"
        story_analysis_path = episode_dir / "story_analysis.json"
        summary_path = episode_dir / "episode_summary.json"
        if not timeline_path.exists() or not story_analysis_path.exists():
            continue

        timeline = load_json(timeline_path)
        story_analysis = load_json(story_analysis_path)
        episode_summary = load_json(summary_path) if summary_path.exists() else None
        result = build_episode_choice_point(
            timeline=timeline,
            story_analysis=story_analysis,
            episode_summary=episode_summary,
            settings=settings,
            model=model,
        )
        save_json(result, episode_dir / "choice_points.json")
        episodes.append(
            {
                "episode_name": episode_dir.name,
                "episode_number": _extract_episode_number(episode_dir.name),
                "choice_point_path": str(episode_dir / "choice_points.json"),
                "choice_point": result.get("choice_point"),
            }
        )

    report = {
        "drama_title": drama_output_dir.name,
        "episode_count": len(episode_dirs),
        "choice_point_count": len([item for item in episodes if item.get("choice_point")]),
        "episodes": episodes,
    }
    save_json(report, drama_output_dir / "choice_points_report.json")
    return report


def _build_choice_candidates(
    timeline: dict[str, Any],
    story_analysis: dict[str, Any],
    episode_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    duration = float(timeline.get("video_info", {}).get("duration") or 0.0)
    ending_hook = str((episode_summary or {}).get("ending_hook", ""))
    highlights = story_analysis.get("highlights", [])
    segments = story_analysis.get("segments", [])
    candidates: list[dict[str, Any]] = []

    for index, highlight in enumerate(highlights, start=1):
        text = " ".join(
            [
                str(highlight.get("title", "")),
                str(highlight.get("type", "")),
                str(highlight.get("reason", "")),
                str(highlight.get("emotion_value", "")),
                " ".join(highlight.get("evidence", [])),
            ]
        )
        score = 70 + _choice_signal_score(text)
        if _is_decision_window(float(highlight.get("start") or 0.0), float(highlight.get("end") or 0.0), duration):
            score += 8
        if ending_hook and _text_overlap(text, ending_hook):
            score += 10
        candidates.append(
            {
                "candidate_id": f"choice_h_{index:02d}",
                "source_type": "highlight",
                "source_ref": f"highlight_{index}",
                "start": float(highlight.get("start") or 0.0),
                "end": float(highlight.get("end") or 0.0),
                "trigger_at": float(highlight.get("trigger_at") or highlight.get("end") or 0.0),
                "pause_at": float(highlight.get("pause_at") or highlight.get("end") or 0.0),
                "title": _clip_text(highlight.get("title"), 80),
                "summary": _clip_text(highlight.get("reason", ""), 140),
                "labels": [str(highlight.get("type", ""))],
                "evidence": _compact_evidence(highlight.get("evidence", [])),
                "candidate_score": score,
            }
        )

    for segment in segments:
        labels = [str(item) for item in segment.get("labels", [])]
        if not set(labels) & {"conflict", "reversal", "suspense", "face_slap"}:
            continue
        text = " ".join(
            [
                str(segment.get("summary", "")),
                str(segment.get("function", "")),
                " ".join(labels),
                " ".join(segment.get("evidence", [])),
            ]
        )
        score = 48 + _choice_signal_score(text)
        if "suspense" in labels or "reversal" in labels:
            score += 10
        if _is_decision_window(float(segment.get("start") or 0.0), float(segment.get("end") or 0.0), duration):
            score += 6
        if ending_hook and _text_overlap(text, ending_hook):
            score += 8
        candidates.append(
            {
                "candidate_id": str(segment.get("segment_id") or "segment"),
                "source_type": "segment",
                "source_ref": str(segment.get("segment_id") or ""),
                "start": float(segment.get("start") or 0.0),
                "end": float(segment.get("end") or 0.0),
                "trigger_at": max(float(segment.get("start") or 0.0), float(segment.get("end") or 0.0) - 0.25),
                "pause_at": float(segment.get("end") or 0.0) + 0.2,
                "title": _clip_text(segment.get("summary", ""), 60),
                "summary": _clip_text(segment.get("summary", ""), 140),
                "labels": labels,
                "evidence": _compact_evidence(segment.get("evidence", [])),
                "candidate_score": score,
            }
        )

    candidates.sort(key=lambda item: (-int(item.get("candidate_score", 0)), float(item.get("start", 0.0))))
    return candidates


def _compact_evidence(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = _clip_text(item, 80)
        if text and text not in result:
            result.append(text)
        if len(result) >= 2:
            break
    return result


def _clip_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _choice_signal_score(text: str) -> int:
    keywords = [
        "离婚",
        "结婚",
        "误会",
        "解释",
        "要不要",
        "能不能",
        "相信",
        "不信",
        "摊牌",
        "真相",
        "回去",
        "留下",
        "离开",
        "救",
        "放手",
        "答应",
        "拒绝",
        "偷情",
        "老公",
        "老婆",
        "分手",
        "选择",
        "决定",
        "回家",
        "见我",
    ]
    strong_count = sum(1 for keyword in keywords if keyword in text)
    question_like = sum(1 for keyword in ["吗", "是不是", "会不会", "为什么", "怎么"] if keyword in text)
    return strong_count * 6 + question_like * 3


def _is_decision_window(start: float, end: float, duration: float) -> bool:
    if duration <= 0:
        return False
    midpoint = (start + end) / 2
    return duration * 0.2 <= midpoint <= duration * 0.9


def _text_overlap(left: str, right: str) -> bool:
    left_tokens = set(_extract_chinese_tokens(left))
    right_tokens = set(_extract_chinese_tokens(right))
    return bool(left_tokens & right_tokens)


def _extract_chinese_tokens(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]{2,}", text)


def _normalize_choice_point(payload: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    raw = payload.get("choice_point")
    if not isinstance(raw, dict):
        return None

    candidate_id = str(raw.get("candidate_id", "")).strip()
    candidate = next((item for item in candidates if item["candidate_id"] == candidate_id), None)
    if candidate is None:
        candidate = candidates[0] if candidates else None
    if candidate is None:
        return None

    options = raw.get("options")
    if not isinstance(options, list) or len(options) < 2:
        options = _default_options(candidate)

    normalized_options: list[dict[str, Any]] = []
    for index, option in enumerate(options[:3]):
        if not isinstance(option, dict):
            continue
        option_id = str(option.get("id") or chr(ord("A") + index))
        normalized_options.append(
            {
                "id": option_id,
                "label": str(option.get("label", "")).strip() or f"选项{option_id}",
                "is_canonical": bool(option.get("is_canonical", False)),
                "outcome_preview": str(option.get("outcome_preview", "")).strip(),
            }
        )
    if len(normalized_options) < 2:
        normalized_options = _default_options(candidate)

    if not any(option["is_canonical"] for option in normalized_options):
        normalized_options[0]["is_canonical"] = True

    alternate_branch = raw.get("alternate_branch") if isinstance(raw.get("alternate_branch"), dict) else {}
    trigger_option_id = str(alternate_branch.get("trigger_option_id", "")).strip()
    if not trigger_option_id:
        non_canonical = next((item["id"] for item in normalized_options if not item["is_canonical"]), normalized_options[-1]["id"])
        trigger_option_id = non_canonical

    return {
        "candidate_id": candidate["candidate_id"],
        "source_type": candidate["source_type"],
        "source_ref": candidate["source_ref"],
        "title": str(raw.get("title", "")).strip() or candidate["title"],
        "choice_type": str(raw.get("choice_type", "")).strip() or _infer_choice_type(candidate),
        "reason": str(raw.get("reason", "")).strip() or candidate["summary"],
        "start": round(float(candidate["start"]), 3),
        "end": round(float(candidate["end"]), 3),
        "trigger_at": round(float(candidate["trigger_at"]), 3),
        "pause_at": round(float(candidate["pause_at"]), 3),
        "question": str(raw.get("question", "")).strip() or _default_question(candidate),
        "options": normalized_options,
        "alternate_branch": {
            "trigger_option_id": trigger_option_id,
            "title": str(alternate_branch.get("title", "")).strip() or "偏离原剧情的短篇分支",
            "divergence": str(alternate_branch.get("divergence", "")).strip() or _default_divergence(candidate),
            "comic_outcome": str(alternate_branch.get("comic_outcome", "")).strip() or _default_comic_outcome(candidate),
        },
        "evidence": candidate["evidence"],
    }


def _build_fallback_choice_point(candidate: dict[str, Any]) -> dict[str, Any]:
    options = _default_options(candidate)
    return {
        "candidate_id": candidate["candidate_id"],
        "source_type": candidate["source_type"],
        "source_ref": candidate["source_ref"],
        "title": candidate["title"] or "关键抉择点",
        "choice_type": _infer_choice_type(candidate),
        "reason": candidate["summary"] or "该段存在明显关系波动或剧情转折，适合插入一次性互动选择。",
        "start": round(float(candidate["start"]), 3),
        "end": round(float(candidate["end"]), 3),
        "trigger_at": round(float(candidate["trigger_at"]), 3),
        "pause_at": round(float(candidate["pause_at"]), 3),
        "question": _default_question(candidate),
        "options": options,
        "alternate_branch": {
            "trigger_option_id": next((item["id"] for item in options if not item["is_canonical"]), "B"),
            "title": "偏离原剧情的短篇分支",
            "divergence": _default_divergence(candidate),
            "comic_outcome": _default_comic_outcome(candidate),
        },
        "evidence": candidate["evidence"],
    }


def _infer_choice_type(candidate: dict[str, Any]) -> str:
    text = " ".join([candidate.get("title", ""), candidate.get("summary", ""), " ".join(candidate.get("evidence", []))])
    mapping = [
        ("trust", ["相信", "误会", "解释"]),
        ("relationship_decision", ["离婚", "结婚", "老公", "老婆", "偷情", "分手"]),
        ("truth_reveal", ["真相", "摊牌", "身份", "曝光"]),
        ("escape_or_stay", ["留下", "离开", "回去", "回家"]),
        ("rescue_or_ignore", ["救", "帮", "放手"]),
    ]
    for choice_type, words in mapping:
        if any(word in text for word in words):
            return choice_type
    return "dramatic_decision"


def _default_question(candidate: dict[str, Any]) -> str:
    choice_type = _infer_choice_type(candidate)
    mapping = {
        "trust": "如果你是主角，此刻你会选择相信对方的解释吗？",
        "relationship_decision": "如果你是主角，此刻你会顺着这段关系继续走下去吗？",
        "truth_reveal": "如果你是主角，此刻你会当场摊牌说出真相吗？",
        "escape_or_stay": "如果你是主角，此刻你会选择留下还是立刻离开？",
        "rescue_or_ignore": "如果你是主角，此刻你会伸手帮他一把吗？",
    }
    return mapping.get(choice_type, "如果你是主角，此刻你会怎么选？")


def _default_options(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    choice_type = _infer_choice_type(candidate)
    if choice_type == "trust":
        return [
            {"id": "A", "label": "先压下情绪，听完解释", "is_canonical": True, "outcome_preview": "剧情继续沿着原有误会与拉扯推进。"},
            {"id": "B", "label": "立刻翻脸，不给解释机会", "is_canonical": False, "outcome_preview": "关系当场失控，进入偏离原剧情的小分支。"},
        ]
    if choice_type == "relationship_decision":
        return [
            {"id": "A", "label": "维持表面平静，按原剧情推进", "is_canonical": True, "outcome_preview": "主线矛盾暂时被压住，后续再爆发。"},
            {"id": "B", "label": "现在就把关系挑明", "is_canonical": False, "outcome_preview": "剧情提前爆炸，进入短篇漫画分支。"},
        ]
    if choice_type == "truth_reveal":
        return [
            {"id": "A", "label": "暂时隐忍，先观察", "is_canonical": True, "outcome_preview": "真相继续在主线里酝酿。"},
            {"id": "B", "label": "当场揭穿所有人", "is_canonical": False, "outcome_preview": "局面立刻失控，出现偏离原作的小结局。"},
        ]
    if choice_type == "escape_or_stay":
        return [
            {"id": "A", "label": "留下，继续正片剧情", "is_canonical": True, "outcome_preview": "主线关系继续纠缠。"},
            {"id": "B", "label": "转身离开", "is_canonical": False, "outcome_preview": "剧情切入一次性离场分支。"},
        ]
    return [
        {"id": "A", "label": "按原剧情继续", "is_canonical": True, "outcome_preview": "故事沿着正片主线推进。"},
        {"id": "B", "label": "做出相反选择", "is_canonical": False, "outcome_preview": "触发一个短篇偏离分支，然后结束。"},
    ]


def _default_comic_outcome(candidate: dict[str, Any]) -> str:
    title = str(candidate.get("title", "")).strip() or "这个关键瞬间"
    evidence = "，".join(candidate.get("evidence", [])[:2])
    choice_type = _infer_choice_type(candidate)
    if choice_type == "relationship_decision":
        return (
            f"主角没有继续维持表面的平静，而是在“{title}”这一刻当场把关系挑明。"
            f" 对方原本还想用含糊态度周旋，却被这一记直球逼得无路可退。"
            f" 现场的暧昧与试探迅速升级成正面冲突，连旁人都察觉到气氛彻底失控。"
            f" 主角丢下更决绝的一句话后转身离开，这段偏离主线的小分支就在最僵的一刻收住。"
        )
    if choice_type == "trust":
        return (
            f"主角没有再给对方任何解释机会，而是在“{title}”之后立刻翻脸。"
            f" 原本还能勉强维持的体面被一句更重的话彻底撕开，{evidence or '双方的矛盾'}一下子摆到明面上。"
            f" 对方试图追上去解释，却只换来更冷的回应。"
            f" 这条偏离主线的漫画分支到两人关系骤冷的瞬间戛然而止。"
        )
    if choice_type == "truth_reveal":
        return (
            f"主角没有再忍，而是在“{title}”这一刻提前把真相摊到了台面上。"
            f" 原本还在暗处运作的人全被打乱节奏，几句关键证词直接让局面翻面。"
            f" 现场短暂陷入死寂后，最心虚的人率先失态，反而暴露了更多破绽。"
            f" 这段偏离正片的小分支停在众人震住的那一秒，适合做漫画插页结尾。"
        )
    if choice_type == "escape_or_stay":
        return (
            f"主角没有像原剧情那样留下，而是在“{title}”之后转身离开。"
            f" 对方显然没料到她会走得这么决绝，追上来时已经错过了最后的解释时机。"
            f" 原本该继续发酵的纠缠被硬生生截断，只留下更大的误会和悬念。"
            f" 这条短篇分支到主角背影消失的画面为止。"
        )
    if choice_type == "rescue_or_ignore":
        return (
            f"主角没有袖手旁观，而是在“{title}”这一刻主动出手改变局面。"
            f" 这一举动让原本失控的节奏突然转向，也让对方第一次对主角产生了新的判断。"
            f" 只是这份介入来得太突然，马上又引出了一个更棘手的小后果。"
            f" 漫画分支就在这次意外救场之后短暂收束。"
        )
    return (
        f"主角在“{title}”这一刻没有顺着原剧情继续，而是做了一个更冒险的反向选择。"
        f" 这一变动让原本压着不爆的矛盾提前炸开，连最会伪装的人也露出了破绽。"
        f" 短短几句交锋就把局势推到了更极端的位置，故事气氛也因此骤然转冷。"
        f" 这条偏离正片的小分支停在后果刚刚显现的节点。"
    )


def _default_divergence(candidate: dict[str, Any]) -> str:
    choice_type = _infer_choice_type(candidate)
    mapping = {
        "relationship_decision": "和原剧情继续压着关系矛盾不同，这条分支会让角色提前把关系说破。",
        "trust": "和原剧情仍保留沟通空间不同，这条分支会让角色当场拒绝信任对方。",
        "truth_reveal": "和原剧情继续隐瞒不同，这条分支会让真相在此刻被提前揭穿。",
        "escape_or_stay": "和原剧情继续停留不同，这条分支会让角色立刻离场。",
        "rescue_or_ignore": "和原剧情的被动旁观不同，这条分支会让角色主动介入。",
    }
    return mapping.get(choice_type, "和原剧情顺势推进不同，这条分支会让角色在此刻做出相反决定。")


def _episode_sort_key(path: Path) -> tuple[int, str]:
    return (_extract_episode_number(path.name), path.name)


def _extract_episode_number(name: str) -> int:
    match = re.search(r"(\d+)", name)
    return int(match.group(1)) if match else 0
