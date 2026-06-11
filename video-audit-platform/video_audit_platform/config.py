import os


def _is_complete_model_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    filenames = set(os.listdir(path))
    if "config.json" not in filenames:
        return False
    has_model_weights = any(
        name.endswith(".safetensors") or name.endswith(".bin") or name.endswith(".pt")
        for name in filenames
    )
    has_sharded_index = "model.safetensors.index.json" in filenames or "pytorch_model.bin.index.json" in filenames
    return has_model_weights or has_sharded_index


def _is_complete_whisper_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    filenames = set(os.listdir(path))
    return "model.bin" in filenames or "config.json" in filenames


def _resolve_existing_path(*candidates, validator=None):
    for candidate in candidates:
        if not candidate:
            continue
        resolved = os.path.abspath(os.path.expanduser(candidate))
        if validator:
            if validator(resolved):
                return resolved
        elif os.path.isdir(resolved):
            return resolved
    return os.path.abspath(os.path.expanduser(candidates[0])) if candidates else ""


DEFAULT_MINICPM_PATH = _resolve_existing_path(
    os.getenv("MINICPMV_PATH"),
    "./models/MiniCPM-V-4.6",
    "./models/MiniCPM-V-4_6",
    "/home/gyfy/projects/视频检测（复件）/models/MiniCPM-V-4_5",
    "/home/gyfy/projects/video_analysis/models/MiniCPM-V-4_5",
    "/home/gyfy/MiniCPM-V-4_5",
    "./models/MiniCPM-V-4_5",
    validator=_is_complete_model_dir,
)

DEFAULT_WHISPER_PATH = _resolve_existing_path(
    os.getenv("WHISPER_MODEL"),
    "/home/gyfy/projects/视频检测（复件）/models/faster-whisper-base",
    "/home/gyfy/projects/video_analysis/models/faster-whisper-base",
    "./models/faster-whisper-base",
    validator=_is_complete_whisper_dir,
)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///project.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HOST = os.getenv("VIDEO_AUDIT_HOST", "0.0.0.0")
    PORT = int(os.getenv("VIDEO_AUDIT_PORT", "5000"))
    DEBUG = os.getenv("VIDEO_AUDIT_DEBUG", "true").lower() == "true"

    PROJECT_ROOT = os.path.abspath(os.getenv("VIDEO_AUDIT_ROOT", os.getcwd()))
    DOWNLOAD_FOLDER = os.path.join(PROJECT_ROOT, "downloaded_videos")

    MINICPMV_PATH = DEFAULT_MINICPM_PATH
    WHISPER_MODEL = DEFAULT_WHISPER_PATH
    ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "int8_float16")
