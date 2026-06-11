# DramaCard 短剧互动卡片项目

DramaCard 是一个围绕短剧内容做“边看边互动”的实验项目。它包含 Android 播放客户端，以及用于从视频中分析剧情、高光点、分支选择点的后端/脚本工具。

这个目录是整理后的开源版本：保留核心代码和工程结构，移除了私有视频、音频、生成素材、模型权重、本地缓存、真实云存储地址和密钥。

## 代码结构

```text
dramacard-open-source/
├── android-client/          # Android 客户端
├── demo/                    # 视频分析与互动点生成 CLI
├── video-audit-platform/    # 视频审核/标注平台原型
├── audio-drama-pipeline/    # 音频剧处理服务原型
├── release/                 # APK 发布产物
└── PROJECT_TECHNICAL_OVERVIEW.md
```

## Android 客户端

目录：`android-client/`

这是面向用户的短剧互动播放器，主要逻辑包括：

- 剧集播放和切集。
- 高光卡自动弹出、收藏和卡册展示。
- 结局/分支选择弹窗，以及选择后的漫画卡展示。
- 点赞、收藏、观看历史、投票、个人资料。
- 退出后保留状态，使用 `SharedPreferences` 存储本地数据。

关键文件：

- `app/src/main/java/com/dramacard/client/data/model/DramaContent.kt`：剧集、高光卡、结局选择等数据模型。
- `app/src/main/java/com/dramacard/client/data/repo/LocalDramaRepository.kt`：本地内容仓库，配置剧集、视频地址、高光卡和分支选择时间点。
- `app/src/main/java/com/dramacard/client/player/PlayerViewModel.kt`：播放器状态、卡片收集、投票、点赞、持久化逻辑。
- `app/src/main/java/com/dramacard/client/player/PlayerScreen.kt`：主要 Compose UI 和播放器交互。
- `app/src/main/assets/README.md`：说明公开版没有附带私有图片素材。

## 视频分析 CLI

目录：`demo/`

这是用于离线分析短剧视频的命令行管线。它从视频中抽帧、OCR 字幕、合并字幕时间轴、理解剧情结构，再产出高光点和分支选择点。

主要流程：

```text
视频 -> 抽帧 -> 字幕区域 OCR -> 字幕清洗 -> 时间轴 -> 剧情分段 -> 高光点/选择点 -> 客户端内容配置
```

关键文件：

- `main.py`：CLI 入口。
- `src/pipeline.py`：单集分析主流程。
- `src/timeline_builder.py`：字幕时间轴构建。
- `src/story_segmenter.py`：剧情分段。
- `src/drama_highlight_reporter.py`：整剧高光点汇总。
- `src/choice_point_builder.py`：分支选择点生成。
- `src/ending_comic_builder.py`：结局漫画 prompt/队列生成。
- `src/llm_client.py`：LLM 调用封装。
- `.env.example`：环境变量模板。

## 视频审核平台

目录：`video-audit-platform/`

这是一个用于查看、审核和调试视频分析结果的平台原型，包含 Flask 后端和简单前端页面。

主要部分：

- `video_audit_platform/app.py`：服务创建入口。
- `video_audit_platform/routes.py`：平台接口路由。
- `video_audit_platform/services/analysis.py`：视频理解、OCR/ASR/模型分析相关逻辑。
- `index.html`：前端页面原型。
- `start_server.sh`：本地启动脚本。

## 音频剧管线

目录：`audio-drama-pipeline/`

这是一个音频剧处理服务原型，包含 Flask 后端、数据结构和前端页面。

关键文件：

- `audio_drama_pipeline/app.py`：应用入口。
- `audio_drama_pipeline/routes.py`：接口路由。
- `audio_drama_pipeline/schemas.py`：数据结构。
- `index.html`：简单前端页面。
- `start_backend.sh`：启动脚本。

`video-audit-platform/audio_drama_pipeline/` 下也保留了一份平台内集成版本。

## 开源版移除了什么

为了避免泄露隐私、版权内容和生产配置，公开副本移除了：

- 原始短剧视频和音频。
- 生成的高光卡、漫画、截图、OCR 结果和分析报告。
- 本地模型权重。
- Python 虚拟环境、Gradle 构建缓存和 IDE 配置。
- `.env`、`local.properties`、真实 API Key。
- 真实云存储/COS 地址，源码中统一替换为 `https://example.com/dramacard-assets`。

## 本地开发需要自己准备

- Android SDK 和 JDK。
- Python 环境和 `requirements.txt` 依赖。
- ffmpeg。
- 测试视频或音频。
- 图片/卡牌/角色素材，或自己的公开素材服务器。
- 如果要调用 LLM 或图像服务，需要自行配置 `.env`。
- 如果要跑本地多模态/ASR/OCR 模型，需要自行下载模型权重。

## 不建议提交到仓库的内容

- `.env`
- `local.properties`
- API Key、Token、云服务密钥
- 原始视频、音频、图片素材
- 生成输出
- 模型权重
- 临时缓存
- 非指定 APK 或压缩包

## 团队分工

**蔡卓颖：客户端开发与交互实现**
负责 Android 客户端整体开发与界面设计，实现短剧列表、视频播放、卡册系统、角色展示以及剧情互动等核心功能；完成客户端与内容配置/接口联调，并负责最终产品展示效果优化与 Demo 录制。

**李沐函：服务端与内容生成模块开发**
负责后台服务架构设计与实现，完成短剧数据管理、高光点下发、互动数据存储等业务逻辑开发；同时负责高光卡牌生成、剧情分支生成、平行结局生成等内容生成模块的设计与实现。

**简子瑜：短剧视频理解与测试验证**
负责短剧视频理解、内容分析与高光识别流程设计，完成剧情标签整理、高光点标注与内容理解模块开发；同时负责系统测试、功能验证以及项目文档整理工作，保障整体系统稳定运行。

## 项目状态

这是一个产品原型级项目，重点展示“短剧视频分析 -> 互动内容配置 -> Android 播放互动”的完整链路。公开版更适合阅读架构、二次开发和替换为自己的内容资产，而不是开箱即用地播放原始私有剧集。

---

# DramaCard

DramaCard is an experimental short-drama interaction project. It includes an Android playback client and tooling for analyzing videos into story timelines, highlight cards, and branch/ending choice points.

This is a sanitized open-source copy. It keeps the core code and project structure, while removing private videos, audio files, generated assets, model weights, local caches, real cloud storage URLs, and secrets.

## Repository Layout

```text
dramacard-open-source/
├── android-client/          # Android client
├── demo/                    # Video analysis and interaction-point CLI
├── video-audit-platform/    # Video review/audit platform prototype
├── audio-drama-pipeline/    # Audio-drama service prototype
├── release/                 # APK release artifact
└── PROJECT_TECHNICAL_OVERVIEW.md
```


## Android Client

Path: `android-client/`

The Android app is the user-facing interactive player. It includes:

- episode playback and episode switching,
- automatic highlight-card popups, collection, and card album views,
- branch/ending choice popups and result comic cards,
- likes, favorites, watch history, voting, and profile state,
- local persistence through `SharedPreferences`.

Key files:

- `app/src/main/java/com/dramacard/client/data/model/DramaContent.kt`: data models for episodes, highlights, and ending choices.
- `app/src/main/java/com/dramacard/client/data/repo/LocalDramaRepository.kt`: local content repository for episodes, media URLs, highlight cards, and choice timestamps.
- `app/src/main/java/com/dramacard/client/player/PlayerViewModel.kt`: player state, card collection, voting, likes, and persistence.
- `app/src/main/java/com/dramacard/client/player/PlayerScreen.kt`: main Compose UI and player interaction layer.
- `app/src/main/assets/README.md`: notes about removed private image assets.

## Video Analysis CLI

Path: `demo/`

This command-line pipeline analyzes short-drama videos offline. It extracts frames, OCRs subtitles, builds a subtitle timeline, understands story structure, and outputs highlight and branch choice points.

Pipeline:

```text
video -> frame extraction -> subtitle OCR -> subtitle cleanup -> timeline -> story segmentation -> highlights/choices -> client content config
```

Key files:

- `main.py`: CLI entry point.
- `src/pipeline.py`: single-episode analysis flow.
- `src/timeline_builder.py`: subtitle timeline builder.
- `src/story_segmenter.py`: story segmentation.
- `src/drama_highlight_reporter.py`: full-drama highlight summarization.
- `src/choice_point_builder.py`: branch choice-point generation.
- `src/ending_comic_builder.py`: ending comic prompt/queue generation.
- `src/llm_client.py`: LLM client wrapper.
- `.env.example`: environment variable template.

## Video Audit Platform

Path: `video-audit-platform/`

This is a Flask-based prototype for reviewing and debugging video analysis results.

Main parts:

- `video_audit_platform/app.py`: app factory.
- `video_audit_platform/routes.py`: platform routes.
- `video_audit_platform/services/analysis.py`: video understanding, OCR/ASR, and model-analysis logic.
- `index.html`: frontend prototype.
- `start_server.sh`: local startup script.

## Audio-Drama Pipeline

Path: `audio-drama-pipeline/`

This is an audio-drama processing service prototype with a Flask backend, schemas, and a simple frontend.

Key files:

- `audio_drama_pipeline/app.py`: app entry point.
- `audio_drama_pipeline/routes.py`: API routes.
- `audio_drama_pipeline/schemas.py`: data schemas.
- `index.html`: simple frontend page.
- `start_backend.sh`: startup script.

An integrated copy also exists under `video-audit-platform/audio_drama_pipeline/`.

## What Was Removed

The public copy removes:

- raw drama video and audio files,
- generated highlight cards, comics, screenshots, OCR results, and reports,
- local model weights,
- Python virtual environments, Gradle build caches, and IDE files,
- `.env`, `local.properties`, and real API keys,
- real cloud storage/COS URLs, replaced with `https://example.com/dramacard-assets`.

## Local Development Requirements

You need to provide:

- Android SDK and JDK,
- Python environment and `requirements.txt` dependencies,
- ffmpeg,
- your own test video or audio files,
- your own image/card/character assets or public asset server,
- local `.env` values if calling LLM or image-generation services,
- local model weights if running multimodal/ASR/OCR models.

## Do Not Commit

- `.env`
- `local.properties`
- API keys, tokens, or cloud secrets
- raw video, audio, or image assets
- generated outputs
- model weights
- temporary caches
- APKs or archives other than the explicitly included release artifact

## Team Roles

**Cai Zhuoying: Android Client Development and Interaction Implementation**
Responsible for the overall development and UI design of the Android client, including the short-drama list, video playback, card album system, character display, and story interaction features. Also completed client-side integration with content configuration/interfaces, optimized the final product presentation, and recorded the demo.

**Li Muhan: Backend and Content Generation Module Development**
Responsible for the backend service architecture and implementation, including short-drama data management, highlight-point delivery, and interaction data storage. Also designed and implemented content generation modules such as highlight card generation, story branch generation, and parallel ending generation.

**Jian Ziyu: Short-Drama Video Understanding and Testing**
Responsible for the design of the short-drama video understanding, content analysis, and highlight recognition workflow, including story tag organization, highlight-point annotation, and content understanding module development. Also handled system testing, functional verification, and project documentation to ensure overall system stability.

## Project Status

This is a product-prototype project that demonstrates the full path from short-drama video analysis to interactive Android playback. The open-source copy is best used for architecture study, secondary development, and replacing the private content layer with your own assets.
