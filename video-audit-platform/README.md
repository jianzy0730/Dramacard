# Short Drama Interaction Platform

基于 MiniCPM-V 4.6、RapidOCR 和 Faster-Whisper 的短剧互动分析后端。当前版本保留了原有的视频上传、镜头切分、抽帧、ASR、多模态分析流程，并在此基础上增强为：

- 跨集剧情记忆持久化
- 高光点识别与 `payoff_score`
- 互动触发点生成
- 字幕 OCR 优先、ASR 兜底的转写链路

## 项目结构

```text
video-audit-platform/
├── appp_api.py                     # 兼容旧启动方式的薄入口
├── index.html                      # 现有前端页面
├── requirements.txt
├── start_server.sh
├── pyproject.toml
└── video_audit_platform/
    ├── __init__.py
    ├── __main__.py                 # python -m video_audit_platform
    ├── app.py                      # Flask app factory
    ├── config.py                   # 配置项
    ├── extensions.py               # db 等扩展
    ├── models.py                   # 数据表与 schema 初始化
    ├── routes.py                   # API 路由
    └── services/
        ├── __init__.py
        └── analysis.py             # 视频分析、剧情记忆、高光识别核心逻辑
```

## 环境要求

- Python 3.10+
- FFmpeg / ffprobe
- 建议 NVIDIA GPU 12GB+ 显存
- 已下载的本地模型目录：
  - MiniCPM 默认优先使用：`./models/MiniCPM-V-4.6`
  - Whisper 默认使用：`/home/gyfy/projects/视频检测（复件）/models/faster-whisper-base`
  - 字幕 OCR 运行时使用：`rapidocr_onnxruntime`

## 安装

```bash
cd video-audit-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果你用 Conda，也可以：

```bash
conda create -n video_audit python=3.10
conda activate video_audit
pip install -r requirements.txt
```

## 启动方式

### 方式 0：新的语音文本驱动版

如果你要跑新的“语音文本驱动短剧高光识别”后端：

```bash
python -m audio_drama_pipeline
```

默认端口：

```text
http://localhost:5001
```

### 方式 1：标准方式

后端：

```bash
python -m video_audit_platform
```

前端：

```bash
python3 -m http.server 8000
```

然后打开 `http://localhost:8000`。

### 方式 2：兼容旧方式

```bash
python appp_api.py
```

这个入口现在只是兼容包装，内部仍然走新的项目结构。

### 方式 3：一键脚本

```bash
chmod +x start_server.sh
./start_server.sh
```

## 常用环境变量

```bash
export MINICPMV_PATH=./models/MiniCPM-V-4.6
export WHISPER_MODEL=/home/gyfy/projects/视频检测（复件）/models/faster-whisper-base
export VIDEO_AUDIT_PORT=5000
export VIDEO_AUDIT_DEBUG=true
```

如果你不手动设置 `MINICPMV_PATH`，项目现在会默认使用：

```bash
./models/MiniCPM-V-4.6
```

## API

### `POST /download`

下载在线视频到 `downloaded_videos/`。

### `POST /analyze`

支持本地文件上传分析，或对已下载文件二次分析。除原有字段外，新增：

- `seriesTitle`
- `seriesKey`
- `episodeNumber`
- `enableOcr`
- `ocrSampleFps`
- `ocrBottomRatio`
- `ocrTextScore`

返回新增：

- `story_context`
- `story_memory`
- `highlights`
- `transcript_pipeline`
- `scene_details[].story_memory`
- `scene_details[].memory_retrieval`
- `scene_details[].highlight`

### `GET /logs`

查看分析历史。

### `GET /series/<series_key>/memory`

查看某个短剧系列的跨集剧情记忆、未解决剧情线和最近记忆事件。

## 我建议你本地这样跑

```bash
cd /home/gyfy/桌面/短剧/video-audit-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m video_audit_platform
```

另开一个终端：

```bash
cd /home/gyfy/桌面/短剧/video-audit-platform
python3 -m http.server 8000
```

最后访问：

```text
http://localhost:8000
```
