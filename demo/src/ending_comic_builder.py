from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .io_utils import load_json, save_json
from .video_utils import extract_frame_at_timestamp, get_video_duration

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def build_drama_ending_comics(
    drama_output_dir: Path,
    drama_video_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    drama_output_dir = drama_output_dir.resolve()
    drama_video_dir = drama_video_dir.resolve()
    output_dir = output_dir.resolve()
    if not drama_output_dir.exists():
        raise FileNotFoundError(f"Drama output directory not found: {drama_output_dir}")
    if not drama_video_dir.exists():
        raise FileNotFoundError(f"Drama video directory not found: {drama_video_dir}")

    episodes: list[dict[str, Any]] = []
    for episode_dir in sorted([path for path in drama_output_dir.iterdir() if path.is_dir()], key=lambda p: _episode_sort_key(p.name)):
        choice_path = episode_dir / "choice_points.json"
        if not choice_path.exists():
            continue
        payload = load_json(choice_path)
        choice_point = payload.get("choice_point")
        if not isinstance(choice_point, dict):
            continue

        episode_name = episode_dir.name
        video_path = _resolve_episode_video_path(drama_video_dir=drama_video_dir, episode_name=episode_name)
        if video_path is None:
            continue

        episode_output_dir = output_dir / episode_name
        panel_refs = _extract_choice_panel_frames(
            choice_point=choice_point,
            video_path=video_path,
            output_dir=episode_output_dir / "frames",
        )
        canonical = _build_canonical_comic(
            episode_name=episode_name,
            choice_point=choice_point,
            panel_refs=panel_refs,
            output_path=episode_output_dir / "ending_A.png",
        )
        alternate = _build_alternate_comic(
            episode_name=episode_name,
            choice_point=choice_point,
            panel_refs=panel_refs,
            output_path=episode_output_dir / "ending_B.png",
        )
        episode_payload = {
            "episode_name": episode_name,
            "title": str(choice_point.get("title", "")),
            "question": str(choice_point.get("question", "")),
            "trigger_at": float(choice_point.get("trigger_at") or 0.0),
            "pause_at": float(choice_point.get("pause_at") or 0.0),
            "options": list(choice_point.get("options", [])),
            "canonical": canonical,
            "alternate": alternate,
        }
        episodes.append(episode_payload)

    manifest = {
        "drama_title": drama_output_dir.name,
        "episode_count": len(episodes),
        "episodes": episodes,
        "notes": [
            "ending_A.png 对应原剧情方向的小结局漫画。",
            "ending_B.png 对应偏离原剧情方向的小结局漫画。",
            "四格漫画使用 2x2 排列，画面只保留对话气泡，不额外加入标题和标签文字。",
        ],
    }
    save_json(manifest, output_dir / "ending_comics_manifest.json")
    return manifest


def _build_canonical_comic(
    episode_name: str,
    choice_point: dict[str, Any],
    panel_refs: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    canonical_option = next((item for item in choice_point.get("options", []) if item.get("is_canonical")), None)
    canonical_label = str(canonical_option.get("label", "按原剧情继续")) if canonical_option else "按原剧情继续"
    preview = str(canonical_option.get("outcome_preview", "故事沿着原剧情继续推进。")) if canonical_option else "故事沿着原剧情继续推进。"
    title = str(choice_point.get("title", "原剧情方向"))
    reason = str(choice_point.get("reason", ""))

    captions = _build_canonical_dialogues(
        title=title,
        canonical_label=canonical_label,
        preview=preview,
        reason=reason,
    )
    _compose_four_panel_comic(
        captions=captions,
        panel_refs=panel_refs,
        output_path=output_path,
        accent="#5BD7FF",
    )
    return {
        "option_id": "A",
        "label": canonical_label,
        "comic_path": str(output_path),
        "summary": preview,
        "captions": captions,
    }


def _build_alternate_comic(
    episode_name: str,
    choice_point: dict[str, Any],
    panel_refs: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    alternate_branch = choice_point.get("alternate_branch") or {}
    alt_option_id = str(alternate_branch.get("trigger_option_id", "B"))
    alt_option = next((item for item in choice_point.get("options", []) if str(item.get("id")) == alt_option_id), None)
    alt_label = str(alt_option.get("label", "偏离原剧情")) if alt_option else "偏离原剧情"
    comic_outcome = _normalize_text(str(alternate_branch.get("comic_outcome", "")))
    divergence = _normalize_text(str(alternate_branch.get("divergence", "")))
    title = str(choice_point.get("title", "偏离原剧情分支"))
    story_beats = _build_alternate_dialogues(
        title=title,
        divergence=divergence,
        comic_outcome=comic_outcome,
        fallback_label=alt_label,
    )

    _compose_four_panel_comic(
        captions=story_beats,
        panel_refs=panel_refs,
        output_path=output_path,
        accent="#FFB15A",
    )
    return {
        "option_id": alt_option_id,
        "label": alt_label,
        "comic_path": str(output_path),
        "summary": comic_outcome,
        "captions": story_beats,
    }


def _compose_four_panel_comic(
    captions: list[str],
    panel_refs: list[dict[str, Any]],
    output_path: Path,
    accent: str,
) -> None:
    width = 1440
    height = 1440
    outer = 24
    gap = 18
    panel_w = (width - outer * 2 - gap) // 2
    panel_h = (height - outer * 2 - gap) // 2

    canvas = Image.new("RGB", (width, height), color="#12161E")
    draw = ImageDraw.Draw(canvas)
    caption_font = _load_font(30)

    _draw_gradient_background(draw, width, height)
    draw.rounded_rectangle((14, 14, width - 14, height - 14), radius=34, outline=accent, width=4)

    for index in range(4):
        row = index // 2
        column = index % 2
        left = outer + column * (panel_w + gap)
        top = outer + row * (panel_h + gap)
        panel_box = (left, top, left + panel_w, top + panel_h)
        ref = panel_refs[index] if index < len(panel_refs) else panel_refs[-1]
        _draw_panel(canvas, panel_box, ref["path"], captions[index], caption_font, accent)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=95)


def _draw_panel(
    canvas: Image.Image,
    panel_box: tuple[int, int, int, int],
    image_path: str,
    caption: str,
    font: ImageFont.FreeTypeFont,
    accent: str,
) -> None:
    left, top, right, bottom = panel_box
    panel = Image.new("RGB", (right - left, bottom - top), color="#111A2C")
    image = Image.open(image_path).convert("RGB")
    crop_bottom = int(image.height * 0.25)
    if crop_bottom > 0:
        image = image.crop((0, 0, image.width, image.height - crop_bottom))
    fitted = ImageOps.fit(image, (right - left, bottom - top), method=Image.Resampling.LANCZOS)
    fitted = _comicize_image(fitted)
    panel.paste(fitted, (0, 0))

    overlay = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, panel.size[0], panel.size[1]), fill=(9, 8, 16, 24))
    panel = Image.alpha_composite(panel.convert("RGBA"), overlay).convert("RGB")
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle((0, 0, panel.size[0] - 1, panel.size[1] - 1), radius=26, outline=accent, width=3)
    _draw_speech_bubble(
        panel=panel,
        text=caption,
        font=font,
        box=(32, 30, panel.size[0] - 32, 210),
        accent=accent,
    )
    canvas.paste(panel, (left, top))


def _draw_gradient_background(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(18 + ratio * 12)
        g = int(22 + ratio * 8)
        b = int(30 + ratio * 10)
        draw.line((0, y, width, y), fill=(r, g, b))


def _extract_choice_panel_frames(
    choice_point: dict[str, Any],
    video_path: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    duration = get_video_duration(video_path)
    start = float(choice_point.get("start") or 0.0)
    end = float(choice_point.get("end") or start)
    trigger_at = float(choice_point.get("trigger_at") or end)
    pause_at = float(choice_point.get("pause_at") or end)
    times = [
        max(0.0, start),
        min(duration, max(start, (start + end) / 2)),
        min(duration, max(start, trigger_at)),
        min(duration, max(start, pause_at)),
    ]

    refs: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, ts in enumerate(times, start=1):
        bucket = int(ts * 3)
        if bucket in seen:
            ts = min(duration, ts + 0.4)
            bucket = int(ts * 3)
        seen.add(bucket)
        frame_path = output_dir / f"panel_{index}.jpg"
        extract_frame_at_timestamp(video_path, frame_path, ts)
        refs.append({"index": index, "timestamp": round(ts, 3), "path": str(frame_path)})
    return refs


def _split_story_into_panels(text: str, fallback_title: str, divergence: str, fallback_label: str) -> list[str]:
    normalized = _normalize_text(text)
    pieces = [piece.strip() for piece in re.split(r"[。！？!?]", normalized) if piece.strip()]
    if len(pieces) >= 4:
        return [_shorten(piece, 36) for piece in pieces[:4]]

    defaults = [
        f"冲突起点：{_shorten(fallback_title, 30)}",
        f"主角做出反向选择：{_shorten(fallback_label, 28)}",
        _shorten(divergence or "局势因为这一选择被提前改写。", 34),
        _shorten(normalized or "分支结局在最紧张的一刻收住。", 36),
    ]
    for index, piece in enumerate(pieces[:4]):
        defaults[index] = _shorten(piece, 36)
    return defaults


def _build_canonical_dialogues(title: str, canonical_label: str, preview: str, reason: str) -> list[str]:
    seeds = [
        "",
        canonical_label or "先按原来的路走。",
        preview,
        title,
    ]
    defaults = [
        "这件事先别在这里掀翻。",
        "先稳住，按原来的节奏走。",
        "这口气先压下去，别让关系彻底失控。",
        "表面恢复平静，但问题根本没有消失。",
    ]
    return [_dialogue_quote(_dialogueize(seed, fallback)) for seed, fallback in zip(seeds, defaults)]


def _build_alternate_dialogues(title: str, divergence: str, comic_outcome: str, fallback_label: str) -> list[str]:
    story_beats = _split_story_into_panels(comic_outcome, fallback_title=title, divergence=divergence, fallback_label=fallback_label)
    defaults = [
        "今天就把这件事彻底说清楚。",
        "既然已经走到这一步，那就别再装下去了。",
        "局势一路失控，所有人都被卷进正面冲突。",
        "从这一刻起，这段关系被改写成另一种结局。",
    ]
    seeds = ["", divergence, story_beats[2], comic_outcome]
    return [_dialogue_quote(_dialogueize(seed, fallback)) for seed, fallback in zip(seeds, defaults)]


def _dialogueize(seed: str, fallback: str) -> str:
    clean = _normalize_text(seed)
    clean = re.sub(r"^[^：:]+[：:]", "", clean)
    clean = re.sub(r"[。！？!?]+$", "", clean)
    if not clean:
        return fallback
    if len(clean) > 16:
        return fallback
    return clean


def _dialogue_quote(text: str) -> str:
    clean = _normalize_text(text).strip("“”\"")
    return f"“{clean}”"


def _comicize_image(image: Image.Image) -> Image.Image:
    base = image.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.SMOOTH_MORE)
    base = ImageEnhance.Color(base).enhance(1.45)
    base = ImageEnhance.Contrast(base).enhance(1.35)
    base = ImageEnhance.Sharpness(base).enhance(1.6)
    base = ImageOps.posterize(base, 4)

    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges)
    edges = ImageEnhance.Contrast(edges).enhance(2.2)
    edges = edges.point(lambda p: 0 if p > 96 else 255)
    edge_rgb = Image.merge("RGB", (edges, edges, edges))

    halftone = image.convert("L").resize((max(1, image.width // 6), max(1, image.height // 6)), Image.Resampling.BILINEAR)
    halftone = halftone.resize(image.size, Image.Resampling.NEAREST)
    halftone = ImageOps.posterize(halftone.convert("RGB"), 3)

    mixed = Image.blend(base, halftone, 0.18)
    mixed = ImageChops.multiply(mixed, edge_rgb)
    return mixed


def _draw_speech_bubble(
    panel: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    box: tuple[int, int, int, int],
    accent: str,
) -> None:
    left, top, right, bottom = box
    draw = ImageDraw.Draw(panel)
    bubble_fill = "#FBF6E9"
    bubble_outline = "#10141D"
    draw.rounded_rectangle((left, top, right, bottom), radius=32, fill=bubble_fill, outline=bubble_outline, width=4)
    tail = [(right - 120, bottom - 4), (right - 70, bottom - 4), (right - 98, bottom + 34)]
    draw.polygon(tail, fill=bubble_fill, outline=bubble_outline)
    wrapped = _wrap_text(text, font=font, max_width=right - left - 48)
    text_box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8)
    text_h = text_box[3] - text_box[1]
    text_y = top + max(22, ((bottom - top) - text_h) // 2 - 2)
    draw.multiline_text((left + 24, text_y), wrapped, font=font, fill="#141821", spacing=8)
    draw.rounded_rectangle((left, top, right, bottom), radius=32, outline=accent, width=2)


def _shorten(text: str, max_chars: int) -> str:
    clean = _normalize_text(text)
    return clean if len(clean) <= max_chars else clean[: max_chars - 1] + "…"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    words: list[str] = []
    buffer = ""
    for char in text:
        buffer += char
        if char in " ，。！？：；,.!?":
            words.append(buffer)
            buffer = ""
    if buffer:
        words.append(buffer)

    lines: list[str] = []
    current = ""
    for piece in words:
        candidate = current + piece
        if font.getlength(candidate) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current.strip())
            current = piece
    if current:
        lines.append(current.strip())
    return "\n".join(lines[:3])


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size=size)


def _episode_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", name)
    return (int(match.group(1)) if match else 0, name)


def _resolve_episode_video_path(drama_video_dir: Path, episode_name: str) -> Path | None:
    for suffix in [".mp4", ".mov", ".mkv"]:
        candidate = drama_video_dir / f"{episode_name}{suffix}"
        if candidate.exists():
            return candidate
    return None
