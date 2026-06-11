import json
import math
import os
import subprocess
import wave
from typing import Dict, List, Tuple

import numpy as np


def probe_video(video_path: str) -> Dict[str, float]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    video_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = float(payload.get("format", {}).get("duration") or 0.0)
    fps_text = video_stream.get("avg_frame_rate") or "0/1"
    num, den = fps_text.split("/", 1)
    fps = float(num) / float(den) if float(den) else 0.0
    return {"duration": duration, "fps": fps}


def extract_audio_to_wav(video_path: str, work_dir: str) -> str:
    os.makedirs(work_dir, exist_ok=True)
    audio_path = os.path.join(work_dir, "audio_track.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr.strip()}")
    return audio_path


def load_pcm_mono(audio_path: str) -> Tuple[np.ndarray, int]:
    with wave.open(audio_path, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, sample_rate


def build_energy_envelope(audio: np.ndarray, sample_rate: int, hop_ms: int = 50) -> Tuple[np.ndarray, float]:
    hop_size = max(1, int(sample_rate * hop_ms / 1000.0))
    if len(audio) == 0:
        return np.zeros(1, dtype=np.float32), hop_ms / 1000.0
    energies: List[float] = []
    for start in range(0, len(audio), hop_size):
        chunk = audio[start:start + hop_size]
        if len(chunk) == 0:
            energies.append(0.0)
            continue
        rms = math.sqrt(float(np.mean(np.square(chunk))))
        energies.append(rms)
    return np.array(energies, dtype=np.float32), hop_ms / 1000.0


def energy_between(envelope: np.ndarray, step_sec: float, start_time: float, end_time: float) -> float:
    if end_time <= start_time:
        return 0.0
    start_idx = max(0, int(start_time / step_sec))
    end_idx = min(len(envelope), max(start_idx + 1, int(math.ceil(end_time / step_sec))))
    window = envelope[start_idx:end_idx]
    return round(float(window.mean()) if len(window) else 0.0, 4)


def enrich_lines_with_audio_features(lines, envelope: np.ndarray, step_sec: float, duration: float):
    if not lines:
        return lines
    for idx, line in enumerate(lines):
        prev_end = lines[idx - 1].end_time if idx > 0 else 0.0
        next_start = lines[idx + 1].start_time if idx + 1 < len(lines) else duration
        line.pause_before = round(max(0.0, line.start_time - prev_end), 3)
        line.pause_after = round(max(0.0, next_start - line.end_time), 3)
        line.speech_energy = energy_between(envelope, step_sec, line.start_time, line.end_time)
        line.pause_energy_before = energy_between(
            envelope,
            step_sec,
            max(0.0, line.start_time - min(0.8, line.pause_before)),
            line.start_time,
        )
        line.pause_energy_after = energy_between(
            envelope,
            step_sec,
            line.end_time,
            min(duration, line.end_time + min(0.8, line.pause_after)),
        )
        reference = max(0.0001, line.speech_energy)
        line.music_bed_score = round(
            max(line.pause_energy_before, line.pause_energy_after) / reference,
            3,
        )
        if idx > 0:
            line.speaker_switch_before = lines[idx - 1].speaker_id != line.speaker_id
            lines[idx - 1].speaker_switch_after = line.speaker_switch_before
    return lines
