import os
import tempfile

from flask import Blueprint, current_app, jsonify, request

from .services.pipeline import run_audio_drama_analysis

api_bp = Blueprint("audio_drama_api", __name__)


def init_app(app):
    app.register_blueprint(api_bp)


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "audio_drama_pipeline"})


@api_bp.route("/analyze", methods=["GET", "POST"])
def analyze():
    if request.method == "GET":
        return jsonify(
            {
                "service": "audio_drama_pipeline",
                "message": "请以 POST 方式上传视频，并可选上传 transcriptFile。",
            }
        )

    if "video" not in request.files or request.files["video"].filename == "":
        return jsonify({"error": "缺少视频文件"}), 400

    video_file = request.files["video"]
    transcript_file = request.files.get("transcriptFile")
    video_path = ""
    transcript_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1] or ".mp4") as tmp_video:
            video_file.save(tmp_video.name)
            video_path = tmp_video.name

        if transcript_file and transcript_file.filename:
            suffix = os.path.splitext(transcript_file.filename)[1] or ".txt"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_transcript:
                transcript_file.save(tmp_transcript.name)
                transcript_path = tmp_transcript.name

        params = {
            "seriesTitle": request.form.get("seriesTitle", ""),
            "seriesKey": request.form.get("seriesKey", ""),
            "episodeNumber": request.form.get("episodeNumber", "1"),
            "asrLanguage": request.form.get("asrLanguage", "zh"),
            "asrBeamSize": request.form.get("asrBeamSize", "8"),
            "speakerMapping": request.form.get("speakerMapping", ""),
            "videoFilename": video_file.filename,
        }
        payload = run_audio_drama_analysis(video_path, transcript_path, params)
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"分析失败: {exc}"}), 500
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        if transcript_path and os.path.exists(transcript_path):
            os.remove(transcript_path)
