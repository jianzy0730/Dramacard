from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import save_json, save_text


def write_timeline(timeline: dict, output_dir: Path) -> Path:
    path = output_dir / "timeline.json"
    save_json(timeline, path)
    return path


def write_report(report_md: str, output_dir: Path) -> Path:
    path = output_dir / "report.md"
    save_text(report_md, path)
    return path


def write_story_analysis(story_analysis: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "story_analysis.json"
    save_json(story_analysis, path)
    return path


def write_episode_summary(episode_summary: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "episode_summary.json"
    save_json(episode_summary, path)
    return path


def write_series_memory(series_memory: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "series_memory.json"
    save_json(series_memory, path)
    return path


def write_choice_points(choice_points: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "choice_points.json"
    save_json(choice_points, path)
    return path


def build_report_from_story_analysis(story_analysis: dict[str, Any]) -> str:
    overview = story_analysis.get("overview", {})
    segments = story_analysis.get("segments", [])
    highlights = story_analysis.get("highlights", [])
    clip_suggestions = story_analysis.get("clip_suggestions", [])
    uncertainties = story_analysis.get("uncertainties", [])

    lines = ["# 视频剧情分析报告", "", "## 一、基础信息", ""]
    lines.extend(
        [
            f"- 视频标题：{overview.get('title', '')}",
            f"- 视频时长：{overview.get('duration_seconds', '')}",
            f"- 主要人物：{_join_character_lines(overview.get('main_characters', []))}",
            f"- 疑似人物关系：{_join_relation_lines(overview.get('relationships', []))}",
            f"- 故事类型：{overview.get('story_type', '')}",
            f"- 核心冲突：{overview.get('core_conflict', '')}",
            "",
            "## 二、逐段时间轴",
            "",
        ]
    )

    for segment in segments:
        lines.extend(
            [
                f"### {segment.get('start', '')}-{segment.get('end', '')}",
                f"- 段落总结：{segment.get('summary', '')}",
                f"- 推测说话人：{segment.get('speaker_guess', '')}",
                f"- 情绪：{segment.get('emotion', '')}",
                f"- 剧情作用：{segment.get('function', '')}",
                f"- 标签：{', '.join(segment.get('labels', []))}",
                f"- 依据：{'; '.join(segment.get('evidence', []))}",
                "",
            ]
        )

    lines.extend(["## 三、高光部分分析", ""])
    for index, highlight in enumerate(highlights, start=1):
        lines.extend(
            [
                f"### 高光点{index}",
                f"- 时间戳：{highlight.get('start', '')}-{highlight.get('end', '')}",
                f"- 触发时间：{highlight.get('trigger_at', '')}",
                f"- 暂停时间：{highlight.get('pause_at', '')}",
                f"- 标题：{highlight.get('title', '')}",
                f"- 高光类型：{highlight.get('type', '')}",
                f"- 为什么是高光：{highlight.get('reason', '')}",
                f"- 爽点/情绪价值：{highlight.get('emotion_value', '')}",
                f"- 钩子价值：{highlight.get('hook', '')}",
                f"- 依据：{'; '.join(highlight.get('evidence', []))}",
                "",
            ]
        )

    lines.extend(["## 四、最佳切片建议", ""])
    for index, clip in enumerate(clip_suggestions, start=1):
        lines.extend(
            [
                f"### 切片{index}",
                f"- 起止时间：{clip.get('start', '')}-{clip.get('end', '')}",
                f"- 触发时间：{clip.get('trigger_at', '')}",
                f"- 暂停时间：{clip.get('pause_at', '')}",
                f"- 标题：{clip.get('title', '')}",
                f"- 开头钩子：{clip.get('opening_hook', '')}",
                f"- 结尾爆点：{clip.get('ending_bang', '')}",
                f"- 推荐原因：{clip.get('reason', '')}",
                "",
            ]
        )

    lines.extend(["## 五、不确定信息", ""])
    for item in uncertainties:
        lines.append(f"- {item}")
    if not uncertainties:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def build_stub_report(timeline: dict, reason: str) -> str:
    duration = timeline.get("video_info", {}).get("duration", "")
    title = timeline.get("video_info", {}).get("title", "")
    event_count = len(timeline.get("events", []))
    return f"""# 视频剧情分析报告

## 1. 基础信息

- 视频文件：{title}
- 视频时长：{duration}
- 时间轴来源：OCR 字幕
- 时间轴事件数：{event_count}

## 2. 状态

LLM 报告生成已跳过。

原因：{reason}

## 3. 下一步

请查看同目录下的 `timeline.json`。配置 `OPENAI_API_KEY` 后去掉 `--skip-llm` 可生成完整剧情分析报告。
"""


def _join_character_lines(characters: list[dict[str, Any]]) -> str:
    if not characters:
        return ""
    return "；".join(
        f"{item.get('name', '')}（{item.get('role', '')}，置信度 {item.get('confidence', '')}）"
        for item in characters
    )


def _join_relation_lines(relationships: list[dict[str, Any]]) -> str:
    if not relationships:
        return ""
    return "；".join(
        f"{item.get('pair', '')}: {item.get('relation', '')}（置信度 {item.get('confidence', '')}）"
        for item in relationships
    )
