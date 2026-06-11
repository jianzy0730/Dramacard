import json
import os
import re
import tempfile
from typing import Any, Dict, Optional

from ..config import Config
from ..schemas import TranscriptLine
from .audio import AUDIO_CLEAN_FILTER, build_energy_envelope, enrich_lines_with_audio_features, extract_audio_to_wav, load_pcm_mono, probe_video
from .highlight import compute_highlights, load_previous_memories, persist_episode_memory
from .transcript import (
    align_script_to_lines,
    assign_speakers,
    load_asr_model,
    parse_optional_transcript,
    parse_speaker_mapping,
    run_asr,
)

_ASR_MODEL = None


def get_asr_model():
    global _ASR_MODEL
    if _ASR_MODEL is None:
        _ASR_MODEL = load_asr_model(Config.WHISPER_MODEL, Config.ASR_COMPUTE_TYPE)
    return _ASR_MODEL


def infer_story_context(video_filename: str, params: Dict[str, Any]) -> Dict[str, Any]:
    base_name = os.path.splitext(os.path.basename(video_filename))[0]
    inferred_title = base_name
    inferred_title = inferred_title.replace("_", " ").replace("-", " ").strip()
    inferred_title = inferred_title.replace("Episode", " ").replace("EP", " ")
    inferred_title = inferred_title.strip()
    inferred_title = re.sub(r"第\s*\d+\s*集", "", inferred_title).strip() or base_name
    series_title = (params.get("seriesTitle") or "").strip() or inferred_title
    series_key = (params.get("seriesKey") or "").strip() or make_series_key(series_title)
    episode_number = int(params.get("episodeNumber") or 1)
    return {
        "series_title": series_title,
        "series_key": series_key,
        "episode_number": episode_number,
    }


def make_series_key(text_value: str) -> str:
    return "series-" + "".join(ch.lower() if ch.isalnum() else "-" for ch in text_value).strip("-")[:48]


def run_audio_drama_analysis(video_path: str, transcript_path: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    context = infer_story_context(params.get("videoFilename", os.path.basename(video_path)), params)
    speaker_mapping = parse_speaker_mapping(params.get("speakerMapping", ""))
    video_meta = probe_video(video_path)

    work_dir = tempfile.mkdtemp(prefix="audio_drama_", dir=Config.WORK_FOLDER)
    audio_path = extract_audio_to_wav(video_path, work_dir)
    audio_pcm, sample_rate = load_pcm_mono(audio_path)
    envelope, step_sec = build_energy_envelope(audio_pcm, sample_rate)

    transcript_source, timed_lines, script_lines = parse_optional_transcript(transcript_path)
    asr_lines = []
    alignment_strategy = "none"
    if transcript_source == "srt":
        lines = timed_lines
    else:
        asr_lines = run_asr(
            get_asr_model(),
            audio_path,
            language=(params.get("asrLanguage") or ""),
            beam_size=int(params.get("asrBeamSize") or 5),
        )
        if transcript_source == "script":
            lines = align_script_to_lines(script_lines, asr_lines)
            alignment_strategy = "script_to_asr_greedy_alignment"
            transcript_source = "script_aligned"
        else:
            lines = asr_lines
            transcript_source = "asr"

    lines, diarization_strategy = assign_speakers(lines, speaker_mapping)
    lines = enrich_lines_with_audio_features(lines, envelope, step_sec, video_meta["duration"])

    previous_events = load_previous_memories(
        Config.MEMORY_FOLDER,
        context["series_key"],
        context["episode_number"],
    )
    highlights, interactions, episode_memory = compute_highlights(lines, previous_events, video_meta["duration"])
    episode_memory.series_key = context["series_key"]
    episode_memory.episode_number = context["episode_number"]
    persist_episode_memory(Config.MEMORY_FOLDER, context["series_key"], context["episode_number"], episode_memory)

    full_transcript = "\n".join(
        f"[{line.start_time:.2f}-{line.end_time:.2f}] {line.character_name or line.speaker_id}: {line.text}"
        for line in lines
    )
    return {
        "story_context": context,
        "pipeline": {
            "mode": "audio_text_driven_highlight_detection",
            "transcript_source": transcript_source,
            "alignment_strategy": alignment_strategy,
            "diarization_strategy": diarization_strategy,
            "line_count": len(lines),
            "asr_model": Config.WHISPER_MODEL,
            "audio_preprocess": AUDIO_CLEAN_FILTER,
        },
        "media": {
            "video_duration": round(video_meta["duration"], 3),
            "video_fps": round(video_meta["fps"], 3),
            "audio_path": audio_path,
        },
        "transcript": {
            "full_text": full_transcript,
            "lines": [line.to_dict() for line in lines],
        },
        "story_memory": episode_memory.to_dict(),
        "highlights": [item.to_dict() for item in highlights],
        "interactions": interactions,
        "speaker_mapping": speaker_mapping,
        "memory_retrieval": {
            "previous_event_count": len(previous_events),
            "previous_events_preview": previous_events[:6],
        },
    }
