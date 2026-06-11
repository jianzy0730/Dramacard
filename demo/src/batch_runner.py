from __future__ import annotations

import re
from pathlib import Path

from .pipeline import analyze


def analyze_dataset(
    dataset_dir: Path,
    output_root: Path,
    language: str = "zh",
    fps: float = 3.0,
    refine_fps: float = 10.0,
    subtitle_crop: str = "bottom",
    crop_y_start: float | None = None,
    crop_y_end: float | None = None,
    llm_model: str | None = None,
    skip_llm: bool = False,
    skip_refine: bool = False,
    keep_artifacts: bool = False,
    skip_existing: bool = False,
) -> list[dict[str, str]]:
    dataset_dir = dataset_dir.resolve()
    output_root = output_root.resolve()
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    results: list[dict[str, str]] = []
    for drama_dir in sorted([path for path in dataset_dir.iterdir() if path.is_dir()], key=lambda path: path.name):
        previous_memory_path: Path | None = None
        episode_paths = sorted(_iter_videos(drama_dir), key=_episode_sort_key)
        for episode_path in episode_paths:
            episode_output_dir = output_root / drama_dir.name / episode_path.stem
            analysis_output = episode_output_dir / "story_analysis.json"
            summary_output = episode_output_dir / "episode_summary.json"
            series_memory_output = episode_output_dir / "series_memory.json"

            if skip_existing and analysis_output.exists():
                results.append(
                    {
                        "video": str(episode_path),
                        "output_dir": str(episode_output_dir),
                        "analysis_path": str(analysis_output),
                        "summary_path": str(summary_output) if summary_output.exists() else "",
                        "series_memory_path": str(series_memory_output) if series_memory_output.exists() else "",
                        "status": "skipped_existing",
                    }
                )
                previous_memory_path = series_memory_output if series_memory_output.exists() else previous_memory_path
                continue

            result = analyze(
                video_path=episode_path,
                output_dir=episode_output_dir,
                language=language,
                fps=fps,
                refine_fps=refine_fps,
                subtitle_crop=subtitle_crop,
                crop_y_start=crop_y_start,
                crop_y_end=crop_y_end,
                previous_memory_path=previous_memory_path,
                llm_model=llm_model,
                skip_llm=skip_llm,
                skip_refine=skip_refine,
                keep_artifacts=keep_artifacts,
            )
            result["video"] = str(episode_path)
            result["output_dir"] = str(episode_output_dir)
            result["status"] = "ok"
            results.append(result)

            series_memory_path = result.get("series_memory_path", "")
            previous_memory_path = Path(series_memory_path) if series_memory_path else previous_memory_path

    return results


def _iter_videos(drama_dir: Path) -> list[Path]:
    extensions = {".mp4", ".mov", ".mkv"}
    return [path for path in drama_dir.iterdir() if path.is_file() and path.suffix.lower() in extensions]


def _episode_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)", path.stem)
    return (int(match.group(1)) if match else 0, path.stem)
