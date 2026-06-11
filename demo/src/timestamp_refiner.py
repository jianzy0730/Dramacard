from __future__ import annotations

import difflib
from pathlib import Path

from .frame_extractor import extract_window_frames
from .ocr_cleaner import clean_ocr_records
from .ocr_engine import run_ocr_on_frame_records
from .subtitle_cropper import CropConfig


def refine_subtitle_timestamps(
    video_path: Path,
    subtitles: list[dict],
    output_dir: Path,
    crop_config: CropConfig,
    refine_fps: float = 10.0,
    window: float = 1.0,
    similarity_threshold: float = 0.85,
) -> list[dict]:
    refined: list[dict] = []
    frame_interval = 1.0 / refine_fps

    for index, subtitle in enumerate(subtitles, start=1):
        start = max(0.0, float(subtitle["start"]) - window)
        end = float(subtitle["end"]) + window
        frames = extract_window_frames(
            video_path=video_path,
            frames_dir=output_dir / f"subtitle_{index:04d}",
            start=start,
            end=end,
            fps=refine_fps,
        )
        raw = run_ocr_on_frame_records(frames, crop_config=crop_config)
        clean = clean_ocr_records(raw)
        matches = [
            record
            for record in clean
            if _similar(str(subtitle["text"]), str(record["text"])) >= similarity_threshold
        ]

        item = dict(subtitle)
        if matches:
            times = [float(record["time"]) for record in matches]
            item["start"] = round(min(times), 3)
            item["end"] = round(max(times) + frame_interval, 3)
            item["confidence"] = round(
                sum(float(record.get("confidence") or 0.0) for record in matches) / len(matches),
                4,
            )
            item["refined"] = True
        else:
            item["refined"] = False
        refined.append(item)
    return refined


def _similar(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return difflib.SequenceMatcher(None, left, right).ratio()
