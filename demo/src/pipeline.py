from __future__ import annotations

from pathlib import Path

from .choice_point_builder import build_episode_choice_point
from .config import load_settings
from .episode_summary_builder import build_episode_summary
from .frame_extractor import extract_frames_with_timestamps
from .io_utils import cleanup_generated_images, load_json, prepare_output_dir, save_json
from .llm_client import analyze_story_with_llm, update_series_memory_with_llm
from .ocr_cleaner import clean_ocr_records
from .ocr_engine import run_ocr_on_frame_records
from .pause_point_refiner import enrich_story_analysis_with_pause_points
from .report_writer import (
    build_report_from_story_analysis,
    build_stub_report,
    write_episode_summary,
    write_report,
    write_choice_points,
    write_series_memory,
    write_story_analysis,
    write_timeline,
)
from .series_memory import compact_series_memory
from .story_segmenter import build_story_segments
from .subtitle_cropper import CropConfig
from .subtitle_merger import merge_subtitles
from .timeline_builder import build_timeline
from .timestamp_refiner import refine_subtitle_timestamps
from .video_utils import get_video_duration


def analyze(
    video_path: Path,
    output_dir: Path,
    language: str = "zh",
    fps: float = 3.0,
    refine_fps: float = 10.0,
    subtitle_crop: str = "bottom",
    crop_y_start: float | None = None,
    crop_y_end: float | None = None,
    previous_memory_path: Path | None = None,
    llm_model: str | None = None,
    skip_llm: bool = False,
    skip_refine: bool = False,
    keep_artifacts: bool = False,
) -> dict[str, str]:
    video_path = video_path.resolve()
    output_dir = output_dir.resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")
    if fps <= 0:
        raise ValueError("--fps must be greater than 0.")
    if refine_fps <= 0:
        raise ValueError("--refine-fps must be greater than 0.")

    settings = load_settings()
    prepare_output_dir(output_dir)
    crop_config = CropConfig(mode=subtitle_crop, y_start=crop_y_start, y_end=crop_y_end)
    previous_memory = _load_previous_memory(previous_memory_path)

    duration = get_video_duration(video_path)
    frame_records = extract_frames_with_timestamps(video_path, output_dir / "frames", fps=fps)

    ocr_raw = run_ocr_on_frame_records(frame_records, crop_config=crop_config)
    save_json(ocr_raw, output_dir / "ocr_raw.json")

    ocr_clean = clean_ocr_records(ocr_raw)
    save_json(ocr_clean, output_dir / "ocr_clean.json")

    subtitle_timeline = merge_subtitles(ocr_clean, frame_interval=1.0 / fps)

    if not skip_refine and subtitle_timeline:
        subtitle_timeline = refine_subtitle_timestamps(
            video_path=video_path,
            subtitles=subtitle_timeline,
            output_dir=output_dir / "refine_frames",
            crop_config=crop_config,
            refine_fps=refine_fps,
            window=1.0,
        )

    save_json(subtitle_timeline, output_dir / "subtitle_timeline.json")

    timeline = build_timeline(
        video_path=video_path,
        duration=duration,
        language=language,
        subtitles=subtitle_timeline,
        gap_threshold=1.0,
    )
    timeline_path = write_timeline(timeline, output_dir)
    segments = build_story_segments(timeline)
    save_json(segments, output_dir / "story_segments.json")
    analysis_path = ""
    summary_path = ""
    series_memory_path = ""
    choice_points_path = ""

    if skip_llm:
        report_md = build_stub_report(timeline, "--skip-llm")
    else:
        story_analysis = analyze_story_with_llm(
            timeline=timeline,
            segments=segments,
            previous_memory=previous_memory,
            settings=settings,
            model=llm_model,
        )
        story_analysis = enrich_story_analysis_with_pause_points(
            story_analysis=story_analysis,
            timeline=timeline,
        )
        analysis_path = str(write_story_analysis(story_analysis, output_dir))
        episode_summary = build_episode_summary(
            story_analysis=story_analysis,
            previous_summary=previous_memory,
        )
        summary_path = str(write_episode_summary(episode_summary, output_dir))
        series_memory = update_series_memory_with_llm(
            previous_memory=previous_memory,
            episode_summary=episode_summary,
            story_analysis=story_analysis,
            settings=settings,
            model=llm_model,
        )
        series_memory = compact_series_memory(series_memory)
        series_memory_path = str(write_series_memory(series_memory, output_dir))
        choice_points = build_episode_choice_point(
            timeline=timeline,
            story_analysis=story_analysis,
            episode_summary=episode_summary,
            settings=settings,
            model=llm_model,
        )
        choice_points_path = str(write_choice_points(choice_points, output_dir))
        report_md = build_report_from_story_analysis(story_analysis)
    report_path = write_report(report_md, output_dir)
    if not keep_artifacts:
        cleanup_generated_images(output_dir)

    return {
        "timeline_path": str(timeline_path),
        "analysis_path": analysis_path,
        "summary_path": summary_path,
        "series_memory_path": series_memory_path,
        "choice_points_path": choice_points_path,
        "report_path": str(report_path),
    }


def _load_previous_memory(previous_memory_path: Path | None) -> dict | None:
    if previous_memory_path is None:
        return None
    path = previous_memory_path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Previous series memory not found: {path}")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Previous series memory must be a JSON object.")
    return compact_series_memory(payload)
