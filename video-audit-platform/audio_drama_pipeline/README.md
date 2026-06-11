# Audio Drama Pipeline

这个并行后端专门用于“语音文本驱动的短剧高光识别”，默认不依赖重视频理解模型。

## 当前流程

1. 上传视频
2. 提取音频
3. 优先读取 `transcriptFile`
4. `SRT` 直接用时间轴
5. `TXT/剧本` 先跑 ASR，再做脚本到 ASR 的轻量对齐
6. 若无剧本，则直接使用 ASR 生成带时间戳台词
7. 给台词分配 `speaker_id`
8. 计算音频能量、停顿、speaker 切换
9. 结合跨集记忆生成 `highlights` 和 `interactions`

## 运行

```bash
cd /home/gyfy/桌面/短剧/video-audit-platform
source .venv/bin/activate
python -m audio_drama_pipeline
```

默认端口：

```text
http://localhost:5001
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

## 输出重点

- `transcript.lines`
- `highlights`
- `interactions`
- `story_memory`
- `memory_retrieval`
