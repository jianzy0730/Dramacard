import os
import tempfile
import traceback

from flask import Blueprint, current_app, jsonify, request

from .models import ensure_database_schema
from .services.analysis import (
    build_series_memory_view,
    download_video,
    list_analysis_logs,
    record_analysis_log,
    run_full_analysis,
)


api_bp = Blueprint("api", __name__)


ANALYZE_GET_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>视频分析接口</title>
    <style>
        body { font-family: sans-serif; text-align: center; padding: 40px; }
        h1 { color: #333; }
        p { color: #666; }
        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>这是一个视频分析的后端接口</h1>
    <p>您不能通过浏览器直接访问这个地址来上传视频。</p>
    <p>请通过我们的前端页面来使用文件上传功能。</p>
    <p>这个地址 (<code>/analyze</code>) 只接受 <code>POST</code> 方法提交的视频文件。</p>
</body>
</html>
"""


def init_app(app):
    with app.app_context():
        ensure_database_schema()
    app.register_blueprint(api_bp)


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api_bp.route("/download", methods=["POST"])
def download_video_endpoint():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "请求中未包含 URL"}), 400

    try:
        payload = download_video(data["url"], current_app.config["DOWNLOAD_FOLDER"])
        return jsonify(payload)
    except Exception as exc:
        print(f"yt-dlp 下载失败: {exc}")
        return jsonify({"error": f"视频下载失败: {str(exc)}"}), 500


@api_bp.route("/analyze", methods=["GET", "POST"])
def analyze_video_endpoint():
    if request.method == "GET":
        return ANALYZE_GET_HTML

    user_ip = request.remote_addr or "unknown"
    is_temp_file = False
    video_path = ""

    if "video" in request.files and request.files["video"].filename != "":
        video_file = request.files["video"]
        video_filename = video_file.filename
        print(f"收到来自 IP [{user_ip}] 的文件上传请求，处理文件: {video_filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            video_file.save(tmp.name)
            video_path = tmp.name
        is_temp_file = True
    elif "filename" in request.form:
        video_filename = request.form.get("filename", "")
        print(f"收到来自 IP [{user_ip}] 的分析请求，处理已下载文件: {video_filename}")
        video_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], video_filename)
        if not os.path.exists(video_path):
            return jsonify({"error": "服务器上找不到指定的已下载文件"}), 404
    else:
        return jsonify({"error": "请求无效，既没有上传文件也没有提供文件名"}), 400

    params = {
        "useSceneDetection": request.form.get("useSceneDetection", "true").lower() == "true",
        "sceneThreshold": float(request.form.get("sceneThreshold", 27.0)),
        "useAdaptive": request.form.get("useAdaptive", "false").lower() == "true",
        "chooseFps": float(request.form.get("chooseFps", 1.5)),
        "maxSide": int(request.form.get("maxSide", 512)),
        "timeScale": float(request.form.get("timeScale", 0.1)),
        "promptText": request.form.get("promptText", ""),
        "enableAsr": request.form.get("enableAsr", "true").lower() == "true",
        "enableOcr": request.form.get("enableOcr", "true").lower() == "true",
        "asrLanguage": request.form.get("asrLanguage", ""),
        "asrBeamSize": int(request.form.get("asrBeamSize", 5)),
        "asrVad": request.form.get("asrVad", "true").lower() == "true",
        "asrMaxChars": int(request.form.get("asrMaxChars", 1200)),
        "ocrSampleFps": float(request.form.get("ocrSampleFps", 2.5)),
        "ocrBottomRatio": float(request.form.get("ocrBottomRatio", 0.32)),
        "ocrTextScore": float(request.form.get("ocrTextScore", 0.45)),
        "maxFramesPerChunk": int(request.form.get("maxFramesPerChunk", 30)),
        "seriesTitle": request.form.get("seriesTitle", ""),
        "seriesKey": request.form.get("seriesKey", ""),
        "episodeNumber": request.form.get("episodeNumber", ""),
        "videoFilename": video_filename,
    }

    try:
        results = run_full_analysis(video_path, params)
        record_analysis_log(user_ip, video_filename, results)
        return jsonify(results)
    except Exception as exc:
        print(f"处理请求时发生严重错误: {exc}")
        traceback.print_exc()
        return jsonify({"error": f"服务器内部错误: {str(exc)}"}), 500
    finally:
        if is_temp_file and os.path.exists(video_path):
            os.remove(video_path)


@api_bp.route("/logs", methods=["GET"])
def get_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    return jsonify(list_analysis_logs(page, per_page))


@api_bp.route("/series/<series_key>/memory", methods=["GET"])
def get_series_memory(series_key):
    payload = build_series_memory_view(series_key)
    if not payload:
        return jsonify({"error": "未找到对应 series_key 的剧情记忆"}), 404
    return jsonify(payload)
