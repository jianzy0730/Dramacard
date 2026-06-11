from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError("ffmpeg not found. Install ffmpeg and make sure it is on PATH.")
    if shutil.which("ffprobe") is None:
        raise FFmpegError("ffprobe not found. Install ffmpeg and make sure ffprobe is on PATH.")


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise FFmpegError(f"Command failed: {' '.join(command)}\n{message}")


def get_video_duration(video_path: Path) -> float:
    require_ffmpeg()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise FFmpegError(completed.stderr.strip())
    payload = json.loads(completed.stdout)
    return float(payload["format"]["duration"])


def extract_frame_at_timestamp(video_path: Path, output_path: Path, timestamp: float) -> Path:
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0.0, timestamp):.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_path),
    ]
    run_command(command)
    return output_path
