import os


def _resolve_existing_path(*candidates):
    for candidate in candidates:
        if not candidate:
            continue
        resolved = os.path.abspath(os.path.expanduser(candidate))
        if os.path.isdir(resolved) and _looks_like_complete_whisper_dir(resolved):
            return resolved
    return ""


def _looks_like_complete_whisper_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    names = set(os.listdir(path))
    has_config = "config.json" in names
    has_weights = "model.bin" in names
    return has_config and has_weights


class Config:
    HOST = os.getenv("AUDIO_DRAMA_HOST", "0.0.0.0")
    PORT = int(os.getenv("AUDIO_DRAMA_PORT", "5001"))
    DEBUG = os.getenv("AUDIO_DRAMA_DEBUG", "true").lower() == "true"

    PROJECT_ROOT = os.path.abspath(os.getenv("AUDIO_DRAMA_ROOT", os.getcwd()))
    DOWNLOAD_FOLDER = os.path.join(PROJECT_ROOT, "downloaded_videos")
    WORK_FOLDER = os.path.join(PROJECT_ROOT, "instance", "audio_drama_pipeline")
    MEMORY_FOLDER = os.path.join(WORK_FOLDER, "memory_store")

    WHISPER_MODEL = (
        _resolve_existing_path(
            os.getenv("WHISPER_MODEL"),
            "./models/faster-whisper-large-v3",
            "/home/gyfy/projects/视频检测（复件）/models/faster-whisper-large-v3",
            "/home/gyfy/projects/video_analysis/models/faster-whisper-large-v3",
            "/home/gyfy/projects/视频检测（复件）/models/faster-whisper-base",
            "/home/gyfy/projects/video_analysis/models/faster-whisper-base",
        )
        or os.getenv("WHISPER_MODEL_REPO", "large-v3")
    )
    ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "int8")
