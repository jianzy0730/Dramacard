import os


class Config:
    HOST = os.getenv("AUDIO_DRAMA_HOST", "0.0.0.0")
    PORT = int(os.getenv("AUDIO_DRAMA_PORT", "5001"))
    DEBUG = os.getenv("AUDIO_DRAMA_DEBUG", "true").lower() == "true"

    PROJECT_ROOT = os.path.abspath(os.getenv("AUDIO_DRAMA_ROOT", os.getcwd()))
    DOWNLOAD_FOLDER = os.path.join(PROJECT_ROOT, "downloaded_videos")
    WORK_FOLDER = os.path.join(PROJECT_ROOT, "instance", "audio_drama_pipeline")
    MEMORY_FOLDER = os.path.join(WORK_FOLDER, "memory_store")

    WHISPER_MODEL = os.path.abspath(
        os.path.expanduser(
            os.getenv(
                "WHISPER_MODEL",
                "/home/gyfy/projects/视频检测（复件）/models/faster-whisper-base",
            )
        )
    )
    ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "int8")
