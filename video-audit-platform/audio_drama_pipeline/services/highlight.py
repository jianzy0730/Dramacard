import json
import os
import re
from typing import Any, Dict, List, Tuple

from ..schemas import EpisodeMemory, Highlight, TranscriptLine


HIGHLIGHT_KEYWORDS = {
    "身份揭露": ["原来", "其实", "真相", "身份", "你是", "竟然"],
    "冲突解决": ["算了", "结束了", "放过", "原谅", "答应", "和好"],
    "关系反转": ["不爱", "背叛", "站住", "离婚", "分手", "合作"],
    "误会解除": ["误会", "不是这样的", "你听我解释", "对不起", "我明白了"],
    "情绪释放": ["终于", "我忍够了", "爱你", "哭", "委屈", "崩溃"],
    "剧尾悬念": ["等等", "怎么会", "不可能", "下一步", "秘密", "别告诉他"],
}

PAYOFF_MAP = {
    "身份揭露": "identity_reveal",
    "冲突解决": "conflict_resolution",
    "关系反转": "relationship_reversal",
    "误会解除": "misunderstanding_release",
    "情绪释放": "emotional_release",
    "剧尾悬念": "cliffhanger",
}

INTERACTION_MAP = {
    "身份揭露": "truth_reveal_card",
    "冲突解决": "choice_resolution",
    "关系反转": "relationship_vote",
    "误会解除": "forgiveness_choice",
    "情绪释放": "emotion_resonance",
    "剧尾悬念": "next_episode_hook",
}


def load_previous_memories(memory_dir: str, series_key: str, episode_number: int) -> List[Dict[str, Any]]:
    if not series_key or not os.path.isdir(memory_dir):
        return []
    items: List[Dict[str, Any]] = []
    prefix = f"{series_key}_ep"
    for filename in sorted(os.listdir(memory_dir)):
        if not filename.startswith(prefix) or not filename.endswith(".json"):
            continue
        path = os.path.join(memory_dir, filename)
        try:
            payload = json.load(open(path, "r", encoding="utf-8"))
        except Exception:
            continue
        if int(payload.get("episode_number", 0) or 0) >= episode_number:
            continue
        for event in payload.get("memory_events", []):
            items.append(event)
    return items


def compute_highlights(
    lines: List[TranscriptLine],
    previous_events: List[Dict[str, Any]],
    episode_duration: float,
) -> Tuple[List[Highlight], List[Dict[str, Any]], EpisodeMemory]:
    highlights: List[Highlight] = []
    interactions: List[Dict[str, Any]] = []
    memory_events: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        highlight_type, semantic_score = classify_highlight_type(line.text, line.end_time, episode_duration)
        memory_matches = match_previous_events(line.text, previous_events)
        speaker_bonus = 0.9 if line.speaker_switch_before or line.speaker_switch_after else 0.0
        pause_bonus = min(1.4, line.pause_after * 1.6 + line.pause_before * 0.7)
        energy_bonus = min(1.2, line.speech_energy * 10.0)
        music_bonus = min(0.8, max(0.0, line.music_bed_score - 0.8))
        memory_bonus = min(2.5, len(memory_matches) * 0.9)
        total_score = semantic_score + speaker_bonus + pause_bonus + energy_bonus + music_bonus + memory_bonus
        if total_score < 2.6:
            continue

        payoff_type = PAYOFF_MAP.get(highlight_type, "dialogue_peak")
        interaction_time = compute_interaction_time(line, lines[idx + 1] if idx + 1 < len(lines) else None)
        trigger_reason = build_trigger_reason(line, highlight_type, memory_matches)
        highlight = Highlight(
            start_time=round(line.start_time, 3),
            end_time=round(line.end_time, 3),
            peak_time=round(max(line.start_time, line.end_time - min(0.18, max(0.05, (line.end_time - line.start_time) * 0.18))), 3),
            interaction_time=interaction_time,
            highlight_type=highlight_type,
            payoff_type=payoff_type,
            key_line=line.text,
            speaker_id=line.speaker_id,
            character_name=line.character_name,
            related_previous_events=memory_matches,
            trigger_reason=trigger_reason,
            interaction_type=INTERACTION_MAP.get(highlight_type, "dialogue_interaction"),
        )
        highlights.append(highlight)
        interactions.append(highlight.to_dict())
        if highlight_type in {"身份揭露", "剧尾悬念", "冲突解决", "关系反转", "误会解除"}:
            memory_events.append(
                {
                    "summary": line.text,
                    "event_type": payoff_type,
                    "speaker_id": line.speaker_id,
                    "character_name": line.character_name,
                    "start_time": line.start_time,
                    "end_time": line.end_time,
                    "is_open_question": highlight_type == "剧尾悬念",
                }
            )

    highlights = dedupe_highlights(highlights)
    interactions = [item.to_dict() if isinstance(item, Highlight) else item for item in highlights]
    summary = build_episode_summary(lines, highlights)
    unresolved_threads = [event for event in memory_events if event.get("is_open_question")]
    episode_memory = EpisodeMemory(
        series_key="",
        episode_number=0,
        episode_summary=summary,
        unresolved_threads=unresolved_threads,
        memory_events=memory_events,
    )
    return highlights, interactions, episode_memory


def classify_highlight_type(text_value: str, end_time: float, duration: float) -> Tuple[str, float]:
    best_type = "情绪释放"
    best_score = 0.4 if text_value else 0.0
    normalized = text_value or ""
    for label, keywords in HIGHLIGHT_KEYWORDS.items():
        score = sum(normalized.count(keyword) for keyword in keywords)
        if label == "剧尾悬念" and end_time >= duration * 0.82:
            score += 1.3
        if score > best_score:
            best_type = label
            best_score = float(score)
    if best_score <= 0.5 and re.search(r"[！？?]", normalized):
        return "情绪释放", 1.0
    return best_type, float(best_score)


def match_previous_events(text_value: str, previous_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    text_tokens = tokenize(text_value)
    scored = []
    for event in previous_events:
        event_text = event.get("summary", "")
        overlap = len(text_tokens & tokenize(event_text))
        if overlap <= 0:
            continue
        scored.append((overlap, event))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [event for _score, event in scored[:3]]


def tokenize(text_value: str):
    return set(re.findall(r"[\u4e00-\u9fff]{1,4}|[A-Za-z0-9_]{2,}", text_value or ""))


def compute_interaction_time(line: TranscriptLine, next_line: TranscriptLine | None) -> float:
    interaction_time = line.end_time
    if line.pause_after >= 0.18:
        interaction_time = min(line.end_time + min(0.35, line.pause_after * 0.6), (next_line.start_time if next_line else line.end_time + 0.35))
    elif next_line:
        interaction_time = max(line.end_time, next_line.start_time - min(0.12, max(0.02, line.pause_after * 0.5)))
    return round(interaction_time, 3)


def build_trigger_reason(line: TranscriptLine, highlight_type: str, memory_matches: List[Dict[str, Any]]) -> str:
    parts = [f"关键台词命中“{highlight_type}”语义"]
    if line.speaker_switch_before or line.speaker_switch_after:
        parts.append("前后存在说话人切换")
    if line.pause_after >= 0.22:
        parts.append("台词后有明显停顿，适合挂互动")
    if line.music_bed_score >= 1.1:
        parts.append("停顿区仍有明显背景能量延续")
    if memory_matches:
        parts.append("与前文剧情记忆形成回收关系")
    return "；".join(parts)


def build_episode_summary(lines: List[TranscriptLine], highlights: List[Highlight]) -> str:
    if not lines:
        return "本集暂无可用台词。"
    lead = "；".join(line.text for line in lines[:3] if line.text)
    tail = "；".join(line.text for line in lines[-2:] if line.text)
    if highlights:
        highlight_desc = "、".join(sorted({item.highlight_type for item in highlights[:4]}))
        return f"本集主要围绕“{lead[:80]}”展开，并在后段推进到“{tail[:80]}”，核心高光集中在{highlight_desc}。"
    return f"本集以“{lead[:80]}”为主线，结尾收束到“{tail[:80]}”。"


def dedupe_highlights(highlights: List[Highlight]) -> List[Highlight]:
    out: List[Highlight] = []
    for item in sorted(highlights, key=lambda obj: (obj.start_time, obj.end_time)):
        if not out:
            out.append(item)
            continue
        prev = out[-1]
        if item.start_time <= prev.end_time + 0.2 and item.highlight_type == prev.highlight_type and item.speaker_id == prev.speaker_id:
            if len(item.key_line) > len(prev.key_line):
                out[-1] = item
            continue
        out.append(item)
    return out


def persist_episode_memory(memory_dir: str, series_key: str, episode_number: int, episode_memory: EpisodeMemory):
    os.makedirs(memory_dir, exist_ok=True)
    episode_memory.series_key = series_key
    episode_memory.episode_number = episode_number
    path = os.path.join(memory_dir, f"{series_key}_ep{episode_number:04d}.json")
    with open(path, "w", encoding="utf-8") as file_obj:
        json.dump(episode_memory.to_dict(), file_obj, ensure_ascii=False, indent=2)
