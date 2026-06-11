from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageDraw

from .io_utils import load_json, save_json


def export_comfy_card_workflows(
    report_path: Path,
    output_dir: Path,
    workflow_template_path: Path,
    load_image_node_id: str = "78",
    prompt_node_id: str = "435",
    save_image_node_id: str = "60",
    negative_prompt_node_id: str = "433:110",
) -> dict[str, Any]:
    report = load_json(report_path.resolve())
    output_dir = output_dir.resolve()
    workflow_template = _load_workflow_template(workflow_template_path)

    drama_title = str(report.get("drama_title", "drama")).strip() or "drama"
    highlights = list(report.get("highlights", []))
    exported: list[dict[str, Any]] = []

    for highlight in highlights:
        contact_sheet_path = _build_contact_sheet_for_highlight(
            highlight=highlight,
            output_dir=output_dir / "input",
        )
        if contact_sheet_path is None:
            exported.append(
                {
                    "highlight_id": highlight.get("highlight_id", ""),
                    "status": "skipped_no_assets",
                }
            )
            continue

        workflow = _render_workflow(
            workflow_template=workflow_template,
            highlight=highlight,
            drama_title=drama_title,
            contact_sheet_filename=contact_sheet_path.name,
            load_image_node_id=load_image_node_id,
            prompt_node_id=prompt_node_id,
            save_image_node_id=save_image_node_id,
            negative_prompt_node_id=negative_prompt_node_id,
        )
        workflow_path = output_dir / "workflows" / f"{highlight.get('highlight_id', 'highlight')}.json"
        save_json(workflow, workflow_path)

        exported.append(
            {
                "highlight_id": highlight.get("highlight_id", ""),
                "episode_name": highlight.get("episode_name", ""),
                "star_level": highlight.get("star_level", 0),
                "card_mode": highlight.get("card_mode", ""),
                "contact_sheet_path": str(contact_sheet_path),
                "workflow_path": str(workflow_path),
                "prompt": str(highlight.get("image_generation_prompt") or highlight.get("card_prompt") or ""),
                "status": "ok",
            }
        )

    manifest = {
        "drama_title": drama_title,
        "report_path": str(report_path.resolve()),
        "workflow_template_path": str(workflow_template_path.resolve()),
        "load_image_node_id": load_image_node_id,
        "prompt_node_id": prompt_node_id,
        "save_image_node_id": save_image_node_id,
        "negative_prompt_node_id": negative_prompt_node_id,
        "export_count": len([item for item in exported if item["status"] == "ok"]),
        "items": exported,
        "notes": [
            "将 output_dir/input 下的拼图素材复制到 ComfyUI 的 input 目录。",
            "将 output_dir/workflows 下的 workflow JSON 导入 ComfyUI，或通过 API 批量提交。",
            "当前 workflow 只支持单张输入图，因此这里把场景参考和角色参考拼成一张 contact sheet。",
        ],
    }
    save_json(manifest, output_dir / "comfy_card_manifest.json")
    return manifest


def _load_workflow_template(path: Path) -> dict[str, Any]:
    payload = load_json(path.resolve())
    if not isinstance(payload, dict):
        raise ValueError("Workflow template must be a JSON object.")
    return payload


def _build_contact_sheet_for_highlight(highlight: dict[str, Any], output_dir: Path) -> Path | None:
    generation_assets = highlight.get("generation_assets", {})
    scene_paths = list(generation_assets.get("scene_reference_paths", []))
    character_paths = list(generation_assets.get("character_reference_paths", []))
    image_paths = [Path(path) for path in [*scene_paths[:4], *character_paths[:2]] if path]
    if not image_paths:
        return None

    tiles = [_load_tile(path) for path in image_paths if path.exists()]
    if not tiles:
        return None

    contact_sheet = _compose_contact_sheet(
        tiles=tiles,
    )
    filename = f"{highlight.get('highlight_id', 'highlight')}_refs.jpg"
    output_path = output_dir / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet.save(output_path, quality=95)
    return output_path


def _load_tile(path: Path) -> Image.Image:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    return rgb


def _compose_contact_sheet(tiles: list[Image.Image]) -> Image.Image:
    tile_width = 768
    tile_height = 768
    columns = 2
    rows = max(1, (len(tiles) + columns - 1) // columns)
    margin = 24
    gutter = 16
    canvas_width = margin * 2 + columns * tile_width + (columns - 1) * gutter
    canvas_height = margin * 2 + rows * tile_height + (rows - 1) * gutter

    canvas = Image.new("RGB", (canvas_width, canvas_height), color=(18, 20, 28))
    draw = ImageDraw.Draw(canvas)

    for index, tile in enumerate(tiles):
        fitted = ImageOps.fit(tile, (tile_width, tile_height), method=Image.Resampling.LANCZOS)
        row = index // columns
        column = index % columns
        x = margin + column * (tile_width + gutter)
        y = margin + row * (tile_height + gutter)
        canvas.paste(fitted, (x, y))
        draw.rectangle(
            [x, y, x + tile_width - 1, y + tile_height - 1],
            outline=(70, 76, 92),
            width=2,
        )

    return canvas


def _render_workflow(
    workflow_template: dict[str, Any],
    highlight: dict[str, Any],
    drama_title: str,
    contact_sheet_filename: str,
    load_image_node_id: str,
    prompt_node_id: str,
    save_image_node_id: str,
    negative_prompt_node_id: str,
) -> dict[str, Any]:
    workflow = copy.deepcopy(workflow_template)
    prompt = _build_consistent_comic_prompt(highlight)
    negative_prompt = _build_negative_prompt()
    save_prefix = _build_save_prefix(drama_title=drama_title, highlight=highlight)

    _require_node(workflow, load_image_node_id)
    _require_node(workflow, prompt_node_id)
    _require_node(workflow, save_image_node_id)

    workflow[load_image_node_id]["inputs"]["image"] = contact_sheet_filename
    workflow[prompt_node_id]["inputs"]["value"] = prompt
    workflow[save_image_node_id]["inputs"]["filename_prefix"] = save_prefix
    if negative_prompt_node_id in workflow:
        workflow[negative_prompt_node_id]["inputs"]["prompt"] = negative_prompt
    return workflow


def _require_node(workflow: dict[str, Any], node_id: str) -> None:
    if node_id not in workflow:
        raise KeyError(f"Workflow node {node_id!r} not found in template.")


def _build_save_prefix(drama_title: str, highlight: dict[str, Any]) -> str:
    drama_slug = _slugify(drama_title)
    episode_slug = _slugify(str(highlight.get("episode_name", "")))
    highlight_id = _slugify(str(highlight.get("highlight_id", "")))
    card_mode = _slugify(str(highlight.get("card_mode", "card")))
    star_level = int(highlight.get("star_level") or 0)
    return f"{drama_slug}/{episode_slug}_{highlight_id}_{card_mode}_{star_level}star"


def _slugify(text: str) -> str:
    safe = "".join(char if char.isalnum() else "_" for char in text.strip())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe or "item"


def _build_consistent_comic_prompt(highlight: dict[str, Any]) -> str:
    card_mode = str(highlight.get("card_mode", "story_card")).strip() or "story_card"
    title = str(highlight.get("title", "")).strip()
    core_content = str(highlight.get("core_content", "")).strip()
    emotion_value = str(highlight.get("emotion_value", "")).strip()
    evidence = "；".join(str(item) for item in highlight.get("evidence", [])[:2] if item)

    mode_clause = (
        "single-panel western comic confrontation card, characters clearly visible, dynamic action pose, expressive body language, bold cinematic framing"
        if card_mode == "scene_card"
        else "single-panel western comic narrative card, symbolic storytelling composition, clear protagonist focus, emotional storytelling, stylized dramatic composition"
    )
    return (
        "high quality western comic collectible card illustration, consistent non-realistic comic style across the whole series, "
        "bold inked lineart, cel shading, graphic shadows, stylized anatomy, comic-book proportions, vibrant but controlled color palette, "
        "polished illustration, vertical single-card composition, not realistic, not photographic, not live action, not 3d render. "
        "absolutely no text, no letters, no words, no chinese characters, no english characters, no subtitle, no speech bubble, no logo, no watermark, no caption, no typography anywhere in the image. "
        f"{mode_clause}. "
        "Preserve the characters' facial features, hairstyle, age, costume feeling, and temperament from the reference images. "
        "Do not add extra people not supported by the references. "
        f"Scene theme: {title}. Story beat: {core_content}. Emotional tone: {emotion_value}. Key cue: {evidence}."
    )


def _build_negative_prompt() -> str:
    return (
        "text, letters, chinese characters, english words, subtitle, caption, speech bubble, logo, watermark, signature, "
        "typography, ui, interface, poster layout, banner, infographic, extra fingers, deformed hands, blurry face, "
        "low detail face, duplicate person, crowd, collage feeling, photo grid, split panel, multiple panels, "
        "realistic, photorealistic, photo, live action, cinematic photo, 3d render, 3d cartoon, clay render"
    )
