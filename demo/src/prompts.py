from __future__ import annotations

import json
from typing import Any


def build_system_prompt() -> str:
    return """你是一个短剧剧情分析师，擅长根据视频字幕时间轴还原剧情、推断人物关系、分析高光点和短视频爆点。

要求：
1. 只能基于输入数据分析，不要编造不存在的信息。
2. 对不确定内容标注“疑似”。
3. 引用关键台词时必须带时间戳。
4. 需要区分“字幕事实”和“剧情推测”。
5. 说话人可以根据上下文推断，但必须说明依据。
6. 输出必须是合法 JSON，不要包裹 Markdown 代码块。
7. 优先给出简洁、结构化、可复用的结论。"""


def build_overview_prompt(
    timeline: dict[str, Any],
    previous_memory: dict[str, Any] | None = None,
) -> str:
    timeline_json = json.dumps(timeline, ensure_ascii=False, indent=2)
    previous_memory_json = json.dumps(previous_memory, ensure_ascii=False, indent=2) if previous_memory else "无"
    return f"""下面是当前集的 OCR 时间轴，以及可选的整部剧前文记忆。

任务：只输出当前集的全局概览，不要分析每个分段。
如果提供了前文记忆，只能作为背景辅助，不能把前文内容误写成当前集事实。

请严格输出 JSON：
{{
  "overview": {{
    "title": 视频标题,
    "duration_seconds": 视频时长,
    "main_characters": [
      {{"name": 名称, "role": 角色定位, "confidence": 0-1, "evidence": [依据]}}
    ],
    "relationships": [
      {{"pair": "人物A-人物B", "relation": 关系, "confidence": 0-1, "evidence": [依据]}}
    ],
    "story_type": 故事类型,
    "core_conflict": 核心冲突
  }},
  "uncertainties": [无法确定的信息]
}}

输入 timeline:
{timeline_json}

前文记忆:
{previous_memory_json}"""


def build_series_memory_prompt(
    previous_memory: dict[str, Any] | None,
    episode_summary: dict[str, Any],
    story_analysis: dict[str, Any],
) -> str:
    previous_memory_json = json.dumps(previous_memory, ensure_ascii=False, indent=2) if previous_memory else "无"
    episode_summary_json = json.dumps(episode_summary, ensure_ascii=False, indent=2)
    story_analysis_json = json.dumps(story_analysis, ensure_ascii=False, indent=2)
    return f"""下面是已有的整部剧前文记忆、当前集摘要和当前集结构化理解。

任务：更新一份可传给下一集的【整部剧前文记忆】。
这份记忆应该覆盖从第 1 集到当前集的累计剧情状态，而不是只摘要当前集。
这份记忆必须保持近似固定长度，不能随着集数增加而无限变长。
这份记忆只用于帮助下一集理解前情，不要做证据追踪，不要记录“哪一集哪句话说过什么”。

请严格输出 JSON：
{{
  "series_memory": {{
    "episodes_covered": 已覆盖到第几集或空字符串,
    "previous_story": "用 120-220 字概括前面大概讲了什么，只写剧情主线，不写证据来源",
    "current_situation": "用 60-120 字描述当前结束时人物关系、主要矛盾和局势推进到哪",
    "character_notes": ["每条 30 字左右，写主要人物目前身份/处境/动机，最多 6 条"],
    "relationship_notes": ["每条 40 字左右，写主要关系现在是什么状态，最多 6 条"],
    "unresolved_hooks": ["每条 40 字左右，写还没解决的大悬念/冲突，最多 6 条"],
    "latest_episode": {{
      "title": "当前集标题",
      "summary": "用 50-90 字概括当前集新增信息",
      "ending_hook": "当前集结尾钩子"
    }}
  }}
}}

要求：
1. 必须整合 previous_memory 和当前集，不要只复述当前集。
2. 只保留后续理解真正有用的前情，删掉重复、细枝末节和低价值事件。
3. 不要输出 evidence、episode_hint、importance、status 等追踪字段。
4. 只能基于输入内容，不要编造新剧情。
5. 不要为了保留所有集而追加流水账，要把旧信息合并成当前状态。
6. 输出应该像给观众看的“前情提要”，不是结构化案卷。

已有前文记忆:
{previous_memory_json}

当前集摘要:
{episode_summary_json}

当前集结构化理解:
{story_analysis_json}"""


def build_segment_batch_prompt(
    segment_batch: list[dict[str, Any]],
    overview: dict[str, Any],
) -> str:
    segments_json = json.dumps(segment_batch, ensure_ascii=False, indent=2)
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    return f"""下面是当前集的一批分段数据，以及该集的全局概览。

任务：只分析这批 segments，不要输出高光和切片建议。

请严格输出 JSON：
{{
  "segments": [
    {{
      "segment_id": 与输入一致,
      "start": 开始时间,
      "end": 结束时间,
      "summary": 该段发生了什么,
      "speaker_guess": 推测主要说话人或"场景字幕",
      "emotion": 情绪,
      "function": 剧情作用,
      "labels": [只能从 "conflict", "reversal", "sweet", "face_slap", "comedy", "suspense", "setup" 中选择],
      "confidence": 0-1,
      "evidence": [关键字幕]
    }}
  ]
}}

输入 overview:
{overview_json}

输入 segments:
{segments_json}"""


def build_highlights_prompt(
    analyzed_segments: list[dict[str, Any]],
    overview: dict[str, Any],
) -> str:
    segments_json = json.dumps(analyzed_segments, ensure_ascii=False, indent=2)
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    return f"""下面是当前集的分段分析结果和全局概览。

任务：只输出 3 到 5 个最有代表性的高光点，不要输出切片建议。

请严格输出 JSON：
{{
  "highlights": [
    {{
      "title": 高光标题,
      "start": 开始时间,
      "end": 结束时间,
      "type": 高光类型,
      "reason": 为什么是高光,
      "emotion_value": 爽点或情绪价值,
      "hook": 是否适合短视频钩子及原因,
      "evidence": [关键字幕]
    }}
  ]
}}

注意：
- `start` 和 `end` 尽量贴近真正的情绪爆点或台词结束点，后处理会基于它们计算 `trigger_at` 和 `pause_at`

输入 overview:
{overview_json}

输入 analyzed segments:
{segments_json}"""


def build_clip_suggestions_prompt(
    analyzed_segments: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
    overview: dict[str, Any],
) -> str:
    segments_json = json.dumps(analyzed_segments, ensure_ascii=False, indent=2)
    highlights_json = json.dumps(highlights, ensure_ascii=False, indent=2)
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    return f"""下面是当前集的全局概览、分段分析结果和高光点。

任务：只输出 2 到 3 个短视频切片建议。

请严格输出 JSON：
{{
  "clip_suggestions": [
    {{
      "start": 开始时间,
      "end": 结束时间,
      "title": 切片标题,
      "opening_hook": 开头钩子,
      "ending_bang": 结尾爆点,
      "reason": 推荐原因
    }}
  ]
}}

输入 overview:
{overview_json}

输入 analyzed segments:
{segments_json}

输入 highlights:
{highlights_json}"""


def build_choice_point_prompt(
    candidates: list[dict[str, Any]],
    overview: dict[str, Any],
    episode_summary: dict[str, Any] | None = None,
) -> str:
    candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    episode_summary_json = json.dumps(episode_summary, ensure_ascii=False, indent=2) if episode_summary else "无"
    return f"""下面是当前集的全局概览、当前集摘要，以及已经筛好的候选互动插入点。

任务：从候选点里只选 1 个最适合插入“单次剧情选择”的位置。

场景要求：
1. 这个选择点应当发生在明显的剧情转折、关系摇摆、误会爆发、真相揭露前后。
2. 这是一次性互动，没有后续多轮分支。
3. 需要给出一个“偏离原剧情”的短篇后续，用于漫画插入，写 3 到 5 句即可，到一个小收束处结束。
4. 不要改写正片主线，只写一个短篇替代分支。

请严格输出 JSON：
{{
  "choice_point": {{
    "candidate_id": "必须从输入 candidates 里选择一个",
    "title": "这个选择点的标题",
    "choice_type": "例如 trust / relationship_decision / truth_reveal / escape_or_stay / rescue_or_ignore / dramatic_decision",
    "reason": "为什么这里适合插入互动",
    "question": "给用户的提问文案",
    "options": [
      {{
        "id": "A",
        "label": "选项文案",
        "is_canonical": true,
        "outcome_preview": "这条会如何贴近原剧情"
      }},
      {{
        "id": "B",
        "label": "选项文案",
        "is_canonical": false,
        "outcome_preview": "这条会如何偏离原剧情"
      }}
    ],
    "alternate_branch": {{
      "trigger_option_id": "触发偏离分支的选项 id",
      "title": "偏离分支标题",
      "divergence": "一句话说明和原剧情的区别",
      "comic_outcome": "3到5句的小段后续，到一个小结尾处结束"
    }}
  }}
}}

输入 overview:
{overview_json}

输入 episode_summary:
{episode_summary_json}

输入 candidates:
{candidates_json}"""
