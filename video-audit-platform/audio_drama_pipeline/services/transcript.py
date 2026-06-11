import json
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from faster_whisper import WhisperModel

from ..schemas import TranscriptLine


def load_asr_model(model_path: str, compute_type: str = "int8"):
    if not os.path.isdir(model_path):
        raise FileNotFoundError(f"Whisper 模型目录不存在: {model_path}")
    try:
        return WhisperModel(model_path, device="cpu", compute_type=compute_type, local_files_only=True)
    except TypeError:
        return WhisperModel(model_path, device="cpu", compute_type=compute_type)


def run_asr(asr_model, audio_path: str, language: str = "", beam_size: int = 5) -> List[TranscriptLine]:
    segments, _info = asr_model.transcribe(
        audio_path,
        language=(None if not language else language),
        beam_size=beam_size,
        vad_filter=True,
        word_timestamps=False,
    )
    lines: List[TranscriptLine] = []
    for seg in segments:
        text_value = (seg.text or "").strip()
        if not text_value:
            continue
        lines.extend(split_segment_to_lines(text_value, float(seg.start), float(seg.end), source="asr"))
    return lines


def split_segment_to_lines(text_value: str, start_time: float, end_time: float, source: str) -> List[TranscriptLine]:
    parts = [part.strip() for part in re.split(r"[。！？!?]+", text_value) if part.strip()]
    if not parts:
        parts = [text_value.strip()]
    duration = max(0.2, end_time - start_time)
    step = duration / max(1, len(parts))
    lines = []
    for idx, part in enumerate(parts):
        line_start = start_time + idx * step
        line_end = min(end_time, line_start + step)
        lines.append(
            TranscriptLine(
                text=part,
                start_time=round(line_start, 3),
                end_time=round(max(line_start + 0.15, line_end), 3),
                source=source,
            )
        )
    return lines


def parse_optional_transcript(file_path: Optional[str]) -> Tuple[str, List[TranscriptLine], List[str]]:
    if not file_path:
        return "none", [], []
    ext = os.path.splitext(file_path)[1].lower()
    raw_text = open(file_path, "r", encoding="utf-8").read()
    if ext == ".srt":
        return "srt", parse_srt(raw_text), []
    return "script", [], parse_script_lines(raw_text)


def parse_srt(raw_text: str) -> List[TranscriptLine]:
    blocks = re.split(r"\n\s*\n", raw_text.strip())
    lines: List[TranscriptLine] = []
    for block in blocks:
        row_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(row_lines) < 2:
            continue
        time_row = row_lines[1] if "-->" in row_lines[1] else row_lines[0]
        text_rows = row_lines[2:] if "-->" in row_lines[1] else row_lines[1:]
        if "-->" not in time_row:
            continue
        start_text, end_text = [item.strip() for item in time_row.split("-->", 1)]
        start_time = srt_time_to_seconds(start_text)
        end_time = srt_time_to_seconds(end_text)
        joined = " ".join(text_rows).strip()
        raw_speaker, cleaned = split_named_line(joined)
        lines.append(
            TranscriptLine(
                text=cleaned,
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                source="srt",
                raw_speaker=raw_speaker,
            )
        )
    return lines


def srt_time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    seconds = float(rest)
    return int(hours) * 3600 + int(minutes) * 60 + seconds


def parse_script_lines(raw_text: str) -> List[str]:
    cleaned = []
    for line in raw_text.splitlines():
        item = line.strip()
        if not item:
            continue
        if re.fullmatch(r"[（(【\[].*[)】\]]", item):
            continue
        cleaned.append(item)
    return cleaned


def split_named_line(text_value: str) -> Tuple[str, str]:
    match = re.match(r"^([\u4e00-\u9fffA-Za-z0-9_]{1,16})[：:]\s*(.+)$", text_value)
    if not match:
        return "", text_value.strip()
    return match.group(1).strip(), match.group(2).strip()


def align_script_to_lines(script_lines: List[str], asr_lines: List[TranscriptLine]) -> List[TranscriptLine]:
    if not script_lines:
        return asr_lines
    if not asr_lines:
        out: List[TranscriptLine] = []
        cursor = 0.0
        for line in script_lines:
            raw_speaker, cleaned = split_named_line(line)
            out.append(
                TranscriptLine(
                    text=cleaned,
                    start_time=round(cursor, 3),
                    end_time=round(cursor + 2.0, 3),
                    source="script_placeholder",
                    raw_speaker=raw_speaker,
                )
            )
            cursor += 2.1
        return out

    aligned: List[TranscriptLine] = []
    cursor = 0
    for script_line in script_lines:
        raw_speaker, cleaned = split_named_line(script_line)
        best_index = cursor
        best_score = -1.0
        for idx in range(cursor, min(len(asr_lines), cursor + 8)):
            score = SequenceMatcher(None, compact_text(cleaned), compact_text(asr_lines[idx].text)).ratio()
            if score > best_score:
                best_score = score
                best_index = idx
        ref = asr_lines[best_index]
        aligned.append(
            TranscriptLine(
                text=cleaned,
                start_time=ref.start_time,
                end_time=ref.end_time,
                source="script_aligned",
                raw_speaker=raw_speaker,
            )
        )
        cursor = min(len(asr_lines) - 1, best_index + 1)
    return aligned


def compact_text(text_value: str) -> str:
    return re.sub(r"\s+", "", text_value or "")


def assign_speakers(lines: List[TranscriptLine], speaker_mapping: Dict[str, str]) -> Tuple[List[TranscriptLine], str]:
    if not lines:
        return lines, "none"
    named_speakers = [line.raw_speaker for line in lines if line.raw_speaker]
    if named_speakers:
        speaker_ids: Dict[str, str] = {}
        for line in lines:
            raw = line.raw_speaker or "旁白"
            if raw not in speaker_ids:
                speaker_ids[raw] = f"speaker_{len(speaker_ids) + 1}"
            line.speaker_id = speaker_ids[raw]
            line.character_name = speaker_mapping.get(line.speaker_id) or raw
        return lines, "script_speaker_tags"

    current_speaker = 1
    previous_text = ""
    for idx, line in enumerate(lines):
        if idx == 0:
            line.speaker_id = "speaker_1"
            line.character_name = speaker_mapping.get(line.speaker_id, "")
            previous_text = line.text
            continue
        pause_before = max(0.0, line.start_time - lines[idx - 1].end_time)
        should_switch = (
            pause_before >= 0.45
            or previous_text.endswith(("吗", "吧", "呢", "？", "?"))
            or len(line.text) <= 8
        )
        if should_switch:
            current_speaker = 1 if current_speaker >= 3 else current_speaker + 1
        line.speaker_id = f"speaker_{current_speaker}"
        line.character_name = speaker_mapping.get(line.speaker_id, "")
        previous_text = line.text
    return lines, "heuristic_turn_taking"


def parse_speaker_mapping(raw_text: str) -> Dict[str, str]:
    if not raw_text.strip():
        return {}
    try:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            return {str(k): str(v) for k, v in payload.items()}
    except Exception:
        pass
    mapping = {}
    for line in raw_text.splitlines():
        if ":" not in line and "：" not in line:
            continue
        left, right = re.split(r"[:：]", line, maxsplit=1)
        mapping[left.strip()] = right.strip()
    return mapping
