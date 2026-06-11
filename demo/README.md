# Video Story Analyzer

一个 OCR-first 的短剧/视频剧情分析工具。

输入 `mp4` 后，本地只做视频抽帧、字幕区域 OCR、字幕清洗、字幕合并和时间戳精修，输出结构化 `timeline.json`。大模型 API 基于 `timeline.json` 和 `story_segments.json` 生成结构化 `story_analysis.json`，`report.md` 仅作为便于人工查看的附带产物。

本项目不使用 Whisper、WhisperX、ASR、pyannote 或说话人分离。

## 安装

确认 `ffmpeg` 可用：

```bash
ffmpeg -version
```

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

复制环境变量文件：

```powershell
copy .env.example .env
```

如需生成 LLM 结构化分析结果，在 `.env` 中填写：

```text
OPENAI_API_KEY=你的_API_Key
LLM_MODEL=gpt-4o-mini
```

## 运行

只生成 OCR 时间轴，不调用 LLM：

```bash
python main.py analyze input.mp4 --output outputs/demo --skip-llm
```

默认会在分析完成后删除 `frames/` 和 `refine_frames/`，只保留 JSON / Markdown 结果；如需保留截图，增加 `--keep-artifacts`。

生成时间轴并调用 LLM，主产物为 `story_analysis.json`：

```bash
python main.py analyze input.mp4 --output outputs/demo
```

带入整部剧前文记忆，增强当前集理解：

```bash
python main.py analyze input.mp4 \
  --output outputs/demo_ep2 \
  --previous-memory outputs/demo_ep1/series_memory.json
```

批量跑完整 dataset，并自动把前面所有集累计成 `series_memory.json`，再传给下一集：

```bash
python main.py analyze-dataset dataset \
  --output outputs/dataset_run \
  --fps 4 \
  --refine-fps 12 \
  --subtitle-crop bottom
```

汇总单部剧的整剧高光点，并导出关键帧图片：

```bash
python main.py build-drama-highlights \
  --drama-output outputs/dataset_run/幸得相遇离婚时 \
  --drama-videos ../dataset/幸得相遇离婚时 \
  --output outputs/drama_highlights/幸得相遇离婚时 \
  --min-episode-gap 3 \
  --per-episode-limit 1
```

常用参数：

```bash
python main.py analyze input.mp4 \
  --output outputs/demo \
  --fps 3 \
  --refine-fps 10 \
  --subtitle-crop bottom \
  --llm-model gpt-4o-mini
```

裁剪模式：

```text
bottom：默认，只 OCR 底部 35% 字幕区域
full：全屏 OCR
custom：自定义高度区间，配合 --crop-y-start / --crop-y-end
```

示例：

```bash
python main.py analyze input.mp4 \
  --output outputs/demo \
  --subtitle-crop custom \
  --crop-y-start 0.60 \
  --crop-y-end 0.95
```

## 输出文件

```text
outputs/demo/
├── frames/
├── refine_frames/
├── ocr_raw.json
├── ocr_clean.json
├── subtitle_timeline.json
├── story_segments.json
├── story_analysis.json
├── episode_summary.json
├── series_memory.json
├── timeline.json
└── report.md
```

`story_analysis.json` 中的高光和切片结果会额外包含：
- `trigger_at`：建议触发互动组件的时间点
- `pause_at`：建议播放器暂停或卡点展示的时间点

`episode_summary.json` 是当前集摘要，供互动点等下游逻辑使用。
`series_memory.json` 是整部剧截至当前集的累计前文记忆，推荐作为下一集分析时的 `--previous-memory` 输入。
`series_memory.json` 会被本地压缩成固定体积的滚动记忆，不会按集数无限追加。

整剧高光汇总命令会输出：
- `drama_highlight_report.json`：整部剧的高光点报告，含高光内容描述、集数、精确时间、星级、卡牌 prompt
- `keyframes/`：每个高光点对应的关键帧图片

默认会按“剧级高光”思路收紧数量：
- 每集最多 1 个
- 相邻高光默认至少隔 2 集
- 默认总数约为全剧集数的 1/3
- 会优先保留剧情主线转折点，如关系变化、身份揭露、回归、危机升级、重大决定等

## 数据流

```text
视频 -> 抽帧 -> 字幕区域裁剪 -> OCR -> 清洗 -> 字幕合并 -> 时间戳精修 -> timeline.json -> 本集理解 story_analysis.json -> 更新前文记忆 series_memory.json -> report.md
```

`story_analysis.json` 是推荐给下游接口直接消费的主结果，`report.md` 只是从该 JSON 渲染出来的阅读版。
