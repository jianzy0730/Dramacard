from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import load_json, save_json


def export_drama_ending_prompts(
    drama_output_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    drama_output_dir = drama_output_dir.resolve()
    output_dir = output_dir.resolve()
    episodes: list[dict[str, Any]] = []

    for episode_dir in sorted([path for path in drama_output_dir.iterdir() if path.is_dir()], key=lambda p: _episode_sort_key(p.name)):
        choice_path = episode_dir / "choice_points.json"
        story_path = episode_dir / "story_analysis.json"
        if not choice_path.exists():
            continue
        choice_payload = load_json(choice_path)
        story_payload = load_json(story_path) if story_path.exists() else {}
        choice_point = choice_payload.get("choice_point")
        if not isinstance(choice_point, dict):
            continue

        episode_name = episode_dir.name
        overview = story_payload.get("overview") or {}
        relationships = overview.get("relationships") or []
        relationship_text = "；".join(str(item.get("relation", "")) for item in relationships if isinstance(item, dict) and item.get("relation")) or "人物关系高度紧张。"
        main_characters = overview.get("main_characters") or []
        character_summary = "；".join(
            f"{item.get('name', '角色')}：{item.get('role', '关键人物')}"
            for item in main_characters[:3]
            if isinstance(item, dict)
        ) or "主角与对手形成强烈戏剧冲突。"

        canonical_option = next((item for item in choice_point.get("options", []) if item.get("is_canonical")), None) or {}
        alternate_branch = choice_point.get("alternate_branch") or {}
        evidence_lines = _extract_evidence_lines(choice_point.get("evidence"))

        canonical_dialogue = _canonical_dialogues(
            title=str(choice_point.get("title", "")),
            label=str(canonical_option.get("label", "按原剧情继续")),
            outcome=str(canonical_option.get("outcome_preview", "故事沿着原剧情继续推进。")),
            reason=str(choice_point.get("reason", "")),
            evidence=evidence_lines,
        )
        alternate_dialogue = _alternate_dialogues(
            title=str(choice_point.get("title", "")),
            divergence=str(alternate_branch.get("divergence", "")),
            outcome=str(alternate_branch.get("comic_outcome", "")),
            evidence=evidence_lines,
        )

        episode_output_dir = output_dir / episode_name
        episode_output_dir.mkdir(parents=True, exist_ok=True)
        prompt_data = {
            "episode_name": episode_name,
            "title": str(choice_point.get("title", "")),
            "question": str(choice_point.get("question", "")),
            "character_summary": character_summary,
            "relationship_summary": relationship_text,
            "A": {
                "label": str(canonical_option.get("label", "按原剧情继续")),
                "dialogues": canonical_dialogue,
                "prompt": _build_prompt(
                    title=str(choice_point.get("title", "")),
                    question=str(choice_point.get("question", "")),
                    character_summary=character_summary,
                    relationship_summary=relationship_text,
                    plot_context=str(choice_point.get("reason", "")),
                    branch_name="A",
                    branch_label=str(canonical_option.get("label", "按原剧情继续")),
                    branch_outcome=str(canonical_option.get("outcome_preview", "故事沿着原剧情继续推进。")),
                    dialogues=canonical_dialogue,
                ),
                "output_path": str(episode_output_dir / "ending_A_ai.png"),
            },
            "B": {
                "label": str(next((item.get("label") for item in choice_point.get("options", []) if str(item.get("id")) == str(alternate_branch.get("trigger_option_id", "B"))), "偏离原剧情")),
                "dialogues": alternate_dialogue,
                "prompt": _build_prompt(
                    title=str(choice_point.get("title", "")),
                    question=str(choice_point.get("question", "")),
                    character_summary=character_summary,
                    relationship_summary=relationship_text,
                    plot_context=str(alternate_branch.get("comic_outcome", "")),
                    branch_name="B",
                    branch_label=str(next((item.get("label") for item in choice_point.get("options", []) if str(item.get("id")) == str(alternate_branch.get("trigger_option_id", "B"))), "偏离原剧情")),
                    branch_outcome=str(alternate_branch.get("comic_outcome", "")),
                    dialogues=alternate_dialogue,
                ),
                "output_path": str(episode_output_dir / "ending_B_ai.png"),
            },
        }
        save_json(prompt_data, episode_output_dir / "prompt_bundle.json")
        episodes.append(prompt_data)

    manifest = {
        "drama_title": drama_output_dir.name,
        "episode_count": len(episodes),
        "episodes": episodes,
    }
    save_json(manifest, output_dir / "ending_prompt_manifest.json")
    return manifest


def _build_prompt(
    title: str,
    question: str,
    character_summary: str,
    relationship_summary: str,
    plot_context: str,
    branch_name: str,
    branch_label: str,
    branch_outcome: str,
    dialogues: list[str],
) -> str:
    dialogue_lines = "\n".join(f"- panel {index + 1}: {line}" for index, line in enumerate(dialogues))
    return f"""Create a single 2x2 four-panel western comic page for a modern Chinese melodrama confrontation or emotional turning point.
Non-photorealistic, premium western comic-book illustration, bold inked line art, cel shading, graphic shadows, expressive faces, elegant but tense body language, dramatic close-up framing, consistent character appearance across all four panels.

Story hook: {title}
Choice question: {question}
Character notes: {character_summary}
Relationship notes: {relationship_summary}
Plot context: {plot_context}
Selected branch: {branch_name} - {branch_label}
Branch outcome: {branch_outcome}

The four panels should read clearly from top-left to bottom-right with escalating dramatic progression. Keep the same core characters across all four panels, make the scene emotionally specific, and avoid random extra people unless the story truly needs background witnesses.

Add only a few small speech bubbles when necessary, using only these exact short Chinese lines:
{dialogue_lines}

Important:
- clear 2x2 comic page layout
- western comic style
- not photorealistic
- no title
- no episode label
- no narration box
- no caption
- no subtitle
- no watermark
- no logo
- no extra text besides the small necessary speech bubbles above
"""


def _canonical_dialogues(title: str, label: str, outcome: str, reason: str, evidence: list[str]) -> list[str]:
    category = _classify_title(title, reason)
    default_by_category = {
        "divorce": ["别在这里说", "我知道了", "先这样", "回头再谈"],
        "reunion": ["你还好吗", "我们是不是见过", "先别多想", "以后再说"],
        "truth": ["先别声张", "我会处理", "别急着下结论", "真相还没到时候"],
        "support": ["别怕", "有我在", "先跟我走", "我会替你撑住"],
        "humiliation": ["适可而止", "别太过分", "先收回这些话", "我不想再听"],
        "contract": ["我知道了", "先让我想想", "先把字放下", "这事没完"],
        "gift": ["不用了", "东西拿走", "我不收", "到这里就够了"],
        "default": ["先别冲动", "我知道了", "先稳住", "这事以后再说"],
    }
    defaults = default_by_category.get(category, default_by_category["default"])
    lines = _pick_dialogue_lines(evidence, defaults)
    return [f"“{_short_line(line, fallback)}”" for line, fallback in zip(lines, defaults)]


def _alternate_dialogues(title: str, divergence: str, outcome: str, evidence: list[str]) -> list[str]:
    category = _classify_title(title, divergence)
    default_by_category = {
        "divorce": ["离婚吧", "我尽快", "你在听吗", "别装了，到此为止"],
        "reunion": ["你到底是谁", "我们一定见过", "别走", "把话说清楚"],
        "truth": ["你还想瞒多久", "今天把真相说清楚", "别再演了", "所有人都听见了"],
        "support": ["别怕", "有我在", "谁也别想逼你", "今天我替你出头"],
        "humiliation": ["你够了", "把话收回去", "谁给你的底气", "现在轮到你难堪了"],
        "contract": ["我不签", "你别逼我", "这不是你说了算", "今天我不会退"],
        "gift": ["我说了不要", "拿回去", "别再来这一套", "以后离我远点"],
        "default": ["今天就说清楚", "你别再装了", "你到底听没听", "到此为止"],
    }
    defaults = default_by_category.get(category, default_by_category["default"])
    lines = _pick_dialogue_lines(evidence, defaults)
    if category == "divorce":
        return [f"“{line}”" for line in defaults]
    return [f"“{_short_line(line, fallback)}”" for line, fallback in zip(lines, defaults)]


def _pick_dialogue_lines(evidence: list[str], defaults: list[str]) -> list[str]:
    cleaned = [_short_line(line, "") for line in evidence if _short_line(line, "")]
    lines: list[str] = []
    used: set[str] = set()
    for item in cleaned:
        if item not in used:
            lines.append(item)
            used.add(item)
        if len(lines) >= 2:
            break
    while len(lines) < 4:
        lines.append(defaults[len(lines)])
    return lines[:4]


def _extract_evidence_lines(evidence: Any) -> list[str]:
    if not isinstance(evidence, list):
        return []
    results: list[str] = []
    for item in evidence:
        if not isinstance(item, str):
            continue
        clean = re.sub(r"^\d+(?:\.\d+)?-\d+(?:\.\d+)?\s*", "", item)
        clean = re.sub(r"^时间戳\d+(?:\.\d+)?-\d+(?:\.\d+)?\s*", "", clean)
        clean = clean.strip("：: ")
        if clean:
            results.append(clean)
    return results


def _classify_title(title: str, reason: str) -> str:
    text = f"{title} {reason}"
    if any(keyword in text for keyword in ["离婚", "原配", "老公"]):
        return "divorce"
    if any(keyword in text for keyword in ["熟悉感", "旧情", "梦", "前任"]):
        return "reunion"
    if any(keyword in text for keyword in ["真相", "揭穿", "摊牌", "指令", "拒婚"]):
        return "truth"
    if any(keyword in text for keyword in ["撑腰", "出头", "守护", "接你", "联系我"]):
        return "support"
    if any(keyword in text for keyword in ["撒泼", "贬低", "羞辱", "质疑", "纠缠", "神经病"]):
        return "humiliation"
    if any(keyword in text for keyword in ["签", "协议", "净身出户", "妥协"]):
        return "contract"
    if any(keyword in text for keyword in ["茶", "还给他", "不要了", "珠宝店"]):
        return "gift"
    return "default"


def _short_line(text: str, fallback: str) -> str:
    clean = re.sub(r"\s+", "", text or "")
    clean = clean.replace("。", "").replace("，", "")
    clean = clean.replace("：", "").replace(":", "")
    if not clean:
        return fallback
    return clean[:14]


def _episode_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", name)
    return (int(match.group(1)) if match else 0, name)
