from __future__ import annotations

from pathlib import Path

from .video_utils import run_command


def extract_frames_with_timestamps(video_path: Path, frames_dir: Path, fps: float) -> list[dict]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    _clear_old_frames(frames_dir)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            str(frames_dir / "frame_%06d.jpg"),
        ]
    )

    records = []
    for index, frame_path in enumerate(sorted(frames_dir.glob("frame_*.jpg")), start=1):
        records.append(
            {
                "frame": frame_path.name,
                "path": str(frame_path),
                "time": round((index - 1) / fps, 3),
                "index": index,
            }
        )
    return records


def extract_window_frames(
    video_path: Path,
    frames_dir: Path,
    start: float,
    end: float,
    fps: float,
) -> list[dict]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    _clear_old_frames(frames_dir)
    start = max(0.0, start)
    duration = max(0.001, end - start)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            str(frames_dir / "frame_%06d.jpg"),
        ]
    )

    records = []
    for index, frame_path in enumerate(sorted(frames_dir.glob("frame_*.jpg")), start=1):
        records.append(
            {
                "frame": frame_path.name,
                "path": str(frame_path),
                "time": round(start + (index - 1) / fps, 3),
                "index": index,
            }
        )
    return records


def _clear_old_frames(frames_dir: Path) -> None:
    for frame_path in frames_dir.glob("frame_*.jpg"):
        frame_path.unlink()
