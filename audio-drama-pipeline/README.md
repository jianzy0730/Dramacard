# Audio Drama Pipeline

这是一个和 `dataset` 平级的独立小项目，专门做“语音文本驱动的短剧高光识别”。

目录位置：

```text
/home/gyfy/桌面/短剧/audio-drama-pipeline
```

## 当前能力

- 从视频提取音频
- 使用 `ffmpeg` 做对白导向的音频清洗前处理
- `SRT` 直接读取时间轴
- `TXT/剧本` 先跑 ASR，再做轻量对齐
- 无剧本时直接 ASR
- 为每句台词分配 `speaker_id`
- 计算停顿、speaker 切换、语音能量、背景能量
- 结合跨集记忆输出 `highlights` 和 `interactions`

## ASR 默认策略

- 优先使用人工 `SRT/TXT`
- 无人工文本时回退到 Whisper ASR
- 默认目标模型：`large-v3`
- 默认语言：`zh`

## 运行后端

如果你继续复用 `video-audit-platform` 里的虚拟环境：

```bash
cd /home/gyfy/桌面/短剧
source /home/gyfy/桌面/短剧/video-audit-platform/.venv/bin/activate
cd /home/gyfy/桌面/短剧/audio-drama-pipeline
python -m audio_drama_pipeline
```

默认端口：

```text
http://localhost:5001
```

## 运行前端

```bash
cd /home/gyfy/桌面/短剧/audio-drama-pipeline
python3 -m http.server 8001
```

打开：

```text
http://localhost:8001
```

## API

### `POST /analyze`

表单字段：

- `video`: 必填，视频文件
- `transcriptFile`: 可选，支持 `.srt` / `.txt`
- `seriesTitle`
- `seriesKey`
- `episodeNumber`
- `asrLanguage`
- `asrBeamSize`
- `speakerMapping`

`speakerMapping` 支持 JSON，例如：

```json
{"speaker_1":"沈知意","speaker_2":"陆沉"}
```
