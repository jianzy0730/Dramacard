import os
import json
import subprocess
import re
import time
import warnings
from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Any, Optional

import torch
from transformers import AutoModel, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer
from transformers.dynamic_module_utils import get_class_from_dynamic_module
from decord import VideoReader, cpu
from scipy.spatial import cKDTree
import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector, AdaptiveDetector
from faster_whisper import WhisperModel
import numpy as np
from PIL import Image
try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None

from ..config import DEFAULT_MINICPM_PATH, DEFAULT_WHISPER_PATH
from ..extensions import db
from ..models import AnalysisLog, StorySeries, EpisodeMemory, StoryMemoryEvent, PlotThreadState

warnings.filterwarnings(
    "ignore",
    message=r".*`use_return_dict` is deprecated! Use `return_dict` instead!.*",
)
warnings.filterwarnings(
    "ignore",
    message=r".*Passing `repetition_penalty` with `inputs_embeds` and without `input_ids` to `generate`.*",
)


def log_progress(message: str):
    print(message, flush=True)


# 全局默认参数

MODEL_PATH_DEFAULT = DEFAULT_MINICPM_PATH
ASR_MODEL_DEFAULT = DEFAULT_WHISPER_PATH
ASR_COMPUTE_TYPE_DEFAULT = "int8_float16"
OCR_SAMPLE_FPS_DEFAULT = 2.5
OCR_BOTTOM_RATIO_DEFAULT = 0.32
OCR_TEXT_SCORE_DEFAULT = 0.45
DRAMA_KEYWORDS = {
    "reveal": ["原来", "其实", "真相", "身份", "不是", "竟然", "居然", "秘密"],
    "conflict": ["你敢", "闭嘴", "滚", "分手", "离婚", "报仇", "误会", "背叛", "威胁"],
    "emotion": ["哭", "崩溃", "委屈", "心疼", "终于", "等了", "忍了", "对不起", "爱你"],
    "decision": ["决定", "答应", "嫁", "走", "留下", "合作", "签字", "选择"],
}


def apply_minicpm_runtime_compat(model_path: str):
    config_path = os.path.join(model_path, "config.json")
    if not os.path.isfile(config_path):
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        auto_map = config_data.get("auto_map", {})
        class_reference = auto_map.get("AutoModel")
        if not class_reference:
            return

        minicpm_cls = get_class_from_dynamic_module(class_reference, model_path, local_files_only=True)
        if getattr(minicpm_cls, "_codex_runtime_compat_patched", False):
            return

        original_init = minicpm_cls.__init__

        def patched_init(self, config, *args, **kwargs):
            original_init(self, config, *args, **kwargs)
            if not hasattr(self, "all_tied_weights_keys"):
                try:
                    self.post_init()
                except Exception as exc:
                    print(f"MiniCPM post_init 兼容补丁执行失败: {exc}")
                    self.all_tied_weights_keys = {}
            elif self.all_tied_weights_keys is None:
                self.all_tied_weights_keys = {}

        minicpm_cls.__init__ = patched_init
        minicpm_cls._codex_runtime_compat_patched = True
        print(f"已应用 MiniCPM 运行时兼容补丁: {class_reference}")
    except Exception as exc:
        print(f"MiniCPM 兼容补丁加载失败，将继续尝试原始加载: {exc}")


def patch_minicpm_tokenizer_compat(tokenizer):
    if tokenizer is None:
        return tokenizer

    token_name_map = {
        "im_start": "<image>",
        "im_end": "</image>",
        "slice_start": "<slice>",
        "slice_end": "</slice>",
        "im_id_start": "<image_id>",
        "im_id_end": "</image_id>",
    }
    for attr_name, token_value in token_name_map.items():
        if not hasattr(tokenizer, attr_name):
            setattr(tokenizer, attr_name, token_value)

    id_attr_map = {
        "im_start_id": "im_start",
        "im_end_id": "im_end",
        "slice_start_id": "slice_start",
        "slice_end_id": "slice_end",
        "im_id_start_id": "im_id_start",
        "im_id_end_id": "im_id_end",
    }
    for id_attr, token_attr in id_attr_map.items():
        if hasattr(tokenizer, id_attr):
            continue
        token_value = getattr(tokenizer, token_attr, None)
        token_id = tokenizer.convert_tokens_to_ids(token_value) if token_value is not None else None
        setattr(tokenizer, id_attr, token_id)

    if not hasattr(tokenizer, "bos_id"):
        setattr(tokenizer, "bos_id", getattr(tokenizer, "bos_token_id", None))
    if not hasattr(tokenizer, "eos_id"):
        setattr(tokenizer, "eos_id", getattr(tokenizer, "eos_token_id", None))
    if not hasattr(tokenizer, "unk_id"):
        setattr(tokenizer, "unk_id", getattr(tokenizer, "unk_token_id", None))
    if not hasattr(tokenizer, "newline_id"):
        setattr(tokenizer, "newline_id", tokenizer.convert_tokens_to_ids("\n"))

    return tokenizer


def analyze_scene_in_chunks(model, tokenizer, scene_data, base_prompt: str, max_frames_per_chunk: int = 30):
    """
    分析一个可能很长的场景，如果帧数超过阈值，则分块处理。
    
    :param scene_data: 单个场景的数据，包含 'frames' 和 'temporal_ids'
    :param base_prompt: 针对该场景的基础提示词
    :param max_frames_per_chunk: 每个分块的最大帧数
    :return: 该场景的完整分析文本
    """
    frames = scene_data["frames"]
    temporal_ids = scene_data["temporal_ids"][0] # temporal_ids 是一个嵌套列表
    
    if len(frames) <= max_frames_per_chunk:
        # 如果帧数没有超过阈值，直接调用原始的 call_chat
        return call_chat(model, tokenizer, frames, [temporal_ids], base_prompt)
    log_progress(f"单元帧数 ({len(frames)}) 超过阈值 ({max_frames_per_chunk})，开始分块处理...")
    
    chunk_analyses = []
    num_chunks = (len(frames) + max_frames_per_chunk - 1) // max_frames_per_chunk
    
    for i in range(num_chunks):
        start_idx = i * max_frames_per_chunk
        end_idx = min((i + 1) * max_frames_per_chunk, len(frames))
        
        chunk_frames = frames[start_idx:end_idx]
        chunk_temporal_ids = temporal_ids[start_idx:end_idx]
        
        # 构造针对每个分块的提示词
        if i == 0:
            # 第一个分块，使用基础提示词
            chunk_prompt = base_prompt
        else:
            # 后续分块，提示模型这是场景的延续
            chunk_prompt = (
                f"这是同一个场景的第 {i+1}/{num_chunks} 部分的延续画面。请继续你的分析。\n"
                f"上一部分的分析摘要是：'{chunk_analyses[-1][:200]}...'\n\n"
                f"现在请基于新的画面进行分析: {base_prompt}"
            )
        
        log_progress(f"  - 正在处理分块 {i+1}/{num_chunks} (帧: {start_idx} to {end_idx})...")
        
        # 对当前分块进行分析
        chunk_result = call_chat(model, tokenizer, chunk_frames, [chunk_temporal_ids], chunk_prompt)
        chunk_analyses.append(chunk_result)
        
        # 强制释放显存，确保每个分块处理前都有干净的状态
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # 将所有分块的分析结果拼接成一个完整的报告
    full_analysis = "\n\n".join(chunk_analyses)
    return full_analysis


def load_model_global(model_path: str, use_quant: bool = False):
    use_cuda = torch.cuda.is_available()
    if use_cuda and torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    elif use_cuda:
        dtype = torch.float16
    else:
        dtype = torch.float32
    model_name = os.path.basename(os.path.normpath(model_path)).lower()
    is_minicpm_v46 = "4.6" in model_name or "4_6" in model_name

    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    if hasattr(processor, "tokenizer"):
        processor.tokenizer = patch_minicpm_tokenizer_compat(processor.tokenizer)
    if use_quant:
        print("警告: 4-bit 量化加载在 API 模式下可能需要额外配置，此处将使用标准加载。")
    if is_minicpm_v46:
        mdl = AutoModelForImageTextToText.from_pretrained(
            model_path,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None,
            torch_dtype=dtype,
        )
    else:
        apply_minicpm_runtime_compat(model_path)
        _ = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=True)
        mdl = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None,
            torch_dtype=dtype,
        )
    if torch.cuda.is_available():
        mdl = mdl.cuda()
    mdl.processor = processor
    mdl._codex_standard_vlm = bool(is_minicpm_v46)
    mdl.eval()
    return mdl, processor, dtype

def load_asr_model_global(model_name: str, compute_type: str = ASR_COMPUTE_TYPE_DEFAULT):
    from pathlib import Path
    os.environ["HF_HUB_OFFLINE"] = "1"

    # 强制在 CPU 上运行 ASR，以彻底绕开 cuDNN 兼容性问题
    device = "cpu"
    # 在 CPU 模式下，compute_type 最好使用 'int8' 以获得最佳性能
    compute_type = "int8" 
    print(f"警告: ASR 模型被强制在 CPU ({compute_type}) 模式下运行以保证兼容性。")
    # ================================================

    model_dir = Path(model_name).expanduser().resolve()
    if not model_dir.exists() or not model_dir.is_dir():
        print(f"错误: ASR 模型目录不存在: {model_dir}")
        return None
    try:
        return WhisperModel(str(model_dir), device=device, compute_type=compute_type, local_files_only=True)
    except TypeError:
        return WhisperModel(str(model_dir), device=device, compute_type=compute_type)


def load_ocr_model_global():
    if RapidOCR is None:
        print("警告: RapidOCR 未安装，字幕 OCR 将自动跳过。")
        return None
    try:
        return RapidOCR()
    except Exception as exc:
        print(f"警告: 字幕 OCR 初始化失败，将跳过 OCR: {exc}")
        return None


_MODEL_BUNDLE: Optional[Tuple[Any, Any, Any, Any, Any]] = None


def get_model_bundle():
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        log_progress("服务器启动中... 正在加载模型，请稍候...")
        log_progress(f"MiniCPM 路径: {MODEL_PATH_DEFAULT}")
        log_progress(f"Whisper 路径: {ASR_MODEL_DEFAULT}")
        model, tokenizer, model_dtype = load_model_global(MODEL_PATH_DEFAULT)
        asr_model = load_asr_model_global(ASR_MODEL_DEFAULT)
        ocr_model = load_ocr_model_global()
        _MODEL_BUNDLE = (model, tokenizer, model_dtype, asr_model, ocr_model)
        log_progress("模型加载完毕！服务器已准备就绪。")
    return _MODEL_BUNDLE


# 所有工具函数 


def dedupe_keep_order(items: List[Any]) -> List[Any]:
    seen = set()
    out = []
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def normalize_character_list(value: Any) -> List[str]:
    items = []
    for item in ensure_list(value):
        if isinstance(item, dict):
            item = item.get("name") or item.get("character") or item.get("title")
        if item is None:
            continue
        text_value = str(item).strip()
        if text_value:
            items.append(text_value)
    return dedupe_keep_order(items)


def clip_text(t: str, max_chars: int) -> str:
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + " ……（已截断）"


def normalize_subtitle_text(text_value: str) -> str:
    text_value = re.sub(r"\s+", "", text_value or "")
    text_value = text_value.replace("|", "1").replace("“", "\"").replace("”", "\"")
    return text_value.strip(" -_.。")


def subtitle_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_subtitle_text(left), normalize_subtitle_text(right)).ratio()


def is_likely_subtitle_text(text_value: str) -> bool:
    cleaned = normalize_subtitle_text(text_value)
    if len(cleaned) < 2 or len(cleaned) > 40:
        return False
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
    latin_chars = re.findall(r"[A-Za-z]", cleaned)
    digits = re.findall(r"\d", cleaned)
    if not cjk_chars and len(latin_chars) + len(digits) >= len(cleaned):
        return False
    return True


def crop_subtitle_region(frame_bgr: np.ndarray, bottom_ratio: float) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    start_y = max(0, int(h * (1.0 - bottom_ratio)))
    start_x = int(w * 0.06)
    end_x = int(w * 0.94)
    crop = frame_bgr[start_y:h, start_x:end_x]
    if crop.size == 0:
        return frame_bgr
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(upscaled, (3, 3), 0)
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)


def extract_ocr_text(ocr_result: Any) -> Tuple[str, float]:
    if not ocr_result:
        return "", 0.0
    texts = []
    scores = []
    for item in ocr_result:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        text_value = str(item[1]).strip()
        if not is_likely_subtitle_text(text_value):
            continue
        try:
            score = float(item[2])
        except Exception:
            score = 0.0
        texts.append(text_value)
        scores.append(score)
    if not texts:
        return "", 0.0
    return "".join(texts).strip(), round(sum(scores) / max(1, len(scores)), 3)


def merge_repeated_segments(segments: List[Dict[str, Any]], similarity_threshold: float = 0.86) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for segment in sorted(segments, key=lambda item: (item["start"], item["end"])):
        if not merged:
            merged.append(dict(segment))
            continue
        last = merged[-1]
        similar = subtitle_similarity(last["text"], segment["text"]) >= similarity_threshold
        contiguous = segment["start"] <= last["end"] + 0.65
        if similar and contiguous and segment.get("source") == last.get("source"):
            last["end"] = max(last["end"], segment["end"])
            if len(normalize_subtitle_text(segment["text"])) > len(normalize_subtitle_text(last["text"])):
                last["text"] = segment["text"]
            if "confidence" in segment or "confidence" in last:
                last["confidence"] = round(
                    (float(last.get("confidence", 0.0)) + float(segment.get("confidence", 0.0))) / 2.0,
                    3,
                )
            continue
        merged.append(dict(segment))
    return merged


def summarize_transcript_hint(text_value: str, max_chars: int = 80) -> str:
    cleaned = re.sub(r"\s+", "", text_value or "")
    return clip_text(cleaned, max_chars) if cleaned else "无明显对白"


def count_keyword_hits(text_value: str, keywords: List[str]) -> int:
    return sum(text_value.count(keyword) for keyword in keywords if keyword)


def estimate_event_salience(transcript: str, duration: float, scene_count: int) -> float:
    transcript = transcript or ""
    keyword_score = (
        count_keyword_hits(transcript, DRAMA_KEYWORDS["reveal"]) * 2.0
        + count_keyword_hits(transcript, DRAMA_KEYWORDS["conflict"]) * 1.5
        + count_keyword_hits(transcript, DRAMA_KEYWORDS["emotion"]) * 1.2
        + count_keyword_hits(transcript, DRAMA_KEYWORDS["decision"]) * 1.0
    )
    punctuation_score = transcript.count("！") * 0.8 + transcript.count("？") * 0.6
    density_score = min(3.0, len(transcript) / 60.0)
    duration_score = 1.0 if 6.0 <= duration <= 24.0 else 0.3
    multi_scene_bonus = 0.6 if scene_count >= 2 else 0.0
    return round(keyword_score + punctuation_score + density_score + duration_score + multi_scene_bonus, 2)


def should_close_event(current_event: Dict[str, Any], next_scene_meta: Optional[Dict[str, float]], params: Dict[str, Any]) -> bool:
    target_duration = float(params.get("targetEventDurationSec", 18.0))
    max_duration = float(params.get("maxEventDurationSec", 30.0))
    max_scenes = int(params.get("maxScenesPerEvent", 4))
    min_transcript_chars = int(params.get("targetEventTranscriptChars", 110))

    duration = current_event["end_time"] - current_event["start_time"]
    transcript_len = len(current_event["transcript"])
    scene_count = len(current_event["scene_indices"])

    if duration >= max_duration or scene_count >= max_scenes:
        return True
    if duration < target_duration and transcript_len < min_transcript_chars:
        return False
    if next_scene_meta is None:
        return True
    gap = float(next_scene_meta["start_time"]) - float(current_event["end_time"])
    current_text = current_event["transcript"]
    strong_end = any(token in current_text for token in ["。", "！", "？", "终于", "原来", "其实"])
    return gap >= 0.35 or strong_end or transcript_len >= min_transcript_chars


def build_story_units(scene_data: List[Dict[str, Any]], scene_transcripts: List[str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not scene_data:
        return []

    units: List[Dict[str, Any]] = []
    current = None

    for idx, (scene, transcript) in enumerate(zip(scene_data, scene_transcripts)):
        meta = scene["meta"]
        transcript = transcript or ""
        if current is None:
            current = {
                "scene_indices": [idx],
                "start_time": float(meta["start_time"]),
                "end_time": float(meta["end_time"]),
                "transcript": transcript,
                "frame_count": len(scene.get("frames", [])),
            }
        else:
            current["scene_indices"].append(idx)
            current["end_time"] = float(meta["end_time"])
            current["transcript"] += transcript
            current["frame_count"] += len(scene.get("frames", []))

        next_meta = scene_data[idx + 1]["meta"] if idx + 1 < len(scene_data) else None
        if should_close_event(current, next_meta, params):
            duration = current["end_time"] - current["start_time"]
            current["unit_index"] = len(units)
            current["scene_count"] = len(current["scene_indices"])
            current["duration"] = duration
            current["transcript_hint"] = summarize_transcript_hint(current["transcript"])
            current["coarse_score"] = estimate_event_salience(current["transcript"], duration, current["scene_count"])
            units.append(current)
            current = None

    if current is not None:
        duration = current["end_time"] - current["start_time"]
        current["unit_index"] = len(units)
        current["scene_count"] = len(current["scene_indices"])
        current["duration"] = duration
        current["transcript_hint"] = summarize_transcript_hint(current["transcript"])
        current["coarse_score"] = estimate_event_salience(current["transcript"], duration, current["scene_count"])
        units.append(current)

    return units


def select_focus_units(units: List[Dict[str, Any]], params: Dict[str, Any]) -> List[int]:
    if not units:
        return []
    max_focus = int(params.get("maxFocusEvents", 8))
    min_focus = int(params.get("minFocusEvents", 2))
    ratio = float(params.get("focusEventRatio", 0.6))
    target_count = max(min_focus, min(max_focus, int(round(len(units) * ratio)) or 1))
    ranked = sorted(units, key=lambda item: (item["coarse_score"], item["duration"]), reverse=True)
    chosen = {item["unit_index"] for item in ranked[:target_count]}
    for item in units:
        if item["coarse_score"] >= 5.0:
            chosen.add(item["unit_index"])
    return sorted(chosen)


def sample_story_unit_frames(unit: Dict[str, Any], scene_data: List[Dict[str, Any]], max_frames: int) -> Tuple[List[Image.Image], List[List[int]]]:
    frames: List[Image.Image] = []
    temporal_ids: List[int] = []
    for scene_index in unit["scene_indices"]:
        frames.extend(scene_data[scene_index].get("frames", []))
        temporal_ids.extend(scene_data[scene_index].get("temporal_ids", [[]])[0])

    if not frames:
        return [Image.new("RGB", (64, 64), color="black")], [[0]]

    if len(frames) <= max_frames:
        return frames, [temporal_ids[:len(frames)] or [0] * len(frames)]

    sampled_indices = np.linspace(0, len(frames) - 1, num=max_frames, dtype=int).tolist()
    sampled_frames = [frames[i] for i in sampled_indices]
    sampled_tids = [temporal_ids[i] for i in sampled_indices] if temporal_ids else list(range(len(sampled_frames)))
    return sampled_frames, [sampled_tids]


def build_story_unit_analysis_prompt(unit: Dict[str, Any], transcript: str, user_prompt: str, is_focus_unit: bool) -> str:
    focus_instruction = (
        "这是候选高光剧情单元，请重点识别冲突升级、身份揭露、关系反转、情绪释放和互动触发点。"
        if is_focus_unit
        else "这是常规剧情单元，请先概括事件推进、人物变化和信息增量。"
    )
    return (
        f"这是短剧的第 {unit['unit_index'] + 1} 个剧情单元，覆盖 {unit['scene_count']} 个镜头场景，"
        f"时间范围 {unit['start_time']:.1f}s - {unit['end_time']:.1f}s。\n"
        f"{focus_instruction}\n"
        f"该剧情单元字幕/转写：{clip_text(transcript or '无', 1600)}\n"
        f"当前单元粗扫线索：{unit['transcript_hint']}，coarse_score={unit['coarse_score']}\n\n"
        f"现在请基于画面和对白进行分析：{user_prompt}"
    )


def make_story_key(raw_text: str, prefix: str) -> str:
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]+', '-', (raw_text or '').strip().lower()).strip('-')
    cleaned = re.sub(r'-{2,}', '-', cleaned)
    if not cleaned:
        cleaned = prefix
    return f"{prefix}-{cleaned[:48]}"


def extract_json_candidate(text_value: str) -> str:
    if not text_value:
        return ""
    stripped = text_value.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped)
        stripped = re.sub(r"```$", "", stripped).strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', stripped)
    return match.group(1) if match else stripped


def parse_model_json_output(raw_text: str, fallback: Any) -> Any:
    try:
        return json.loads(extract_json_candidate(raw_text))
    except Exception:
        return fallback


def extract_episode_number(text_value: str) -> Optional[int]:
    if not text_value:
        return None
    patterns = [
        r'第\s*(\d+)\s*集',
        r'[Ee]pisode[\s_-]*(\d+)',
        r'\b[Ee][Pp]?[\s_-]?(\d+)\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text_value)
        if match:
            return int(match.group(1))
    return None


def infer_story_context(video_filename: str, params: Dict[str, Any]) -> Dict[str, Any]:
    series_title = (params.get('seriesTitle') or '').strip()
    series_key = (params.get('seriesKey') or '').strip()
    episode_number = params.get('episodeNumber')
    if isinstance(episode_number, str) and episode_number.strip():
        episode_number = int(episode_number)
    base_name = os.path.splitext(os.path.basename(video_filename))[0]
    inferred_episode = extract_episode_number(base_name)
    episode_number = episode_number or inferred_episode or 1
    if not series_title:
        series_title = re.sub(r'第\s*\d+\s*集', '', base_name, flags=re.IGNORECASE).strip(" -_") or base_name
    if not series_key:
        series_key = make_story_key(series_title, "series")
    return {
        "series_title": series_title,
        "series_key": series_key,
        "episode_number": int(episode_number),
    }


def tokenize_story_text(text_value: str) -> List[str]:
    if not text_value:
        return []
    tokens = re.findall(r'[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_]{2,}', text_value.lower())
    return dedupe_keep_order(tokens[:64])


def safe_temporal_ids(scene_temporal_ids: List[List[int]], limit: int = 1) -> List[List[int]]:
    if scene_temporal_ids and scene_temporal_ids[0]:
        return [scene_temporal_ids[0][:limit]]
    return [[0]]


def call_structured_chat(model, tokenizer, frames, temporal_ids, prompt: str, fallback: Any) -> Any:
    try:
        raw = call_chat(model, tokenizer, frames, temporal_ids, prompt)
        parsed = parse_model_json_output(raw, fallback)
        return parsed if parsed is not None else fallback
    except Exception as exc:
        print(f"结构化调用失败: {exc}")
        return fallback


def normalize_scene_story_payload(payload: Dict[str, Any], scene_index: int, scene_meta: Dict[str, float]) -> Dict[str, Any]:
    payload = payload or {}
    characters = normalize_character_list(payload.get("characters"))
    conflicts = []
    for item in ensure_list(payload.get("conflicts")):
        if not isinstance(item, dict):
            continue
        conflicts.append({
            "thread_hint": item.get("thread_hint", "")[:120],
            "status": item.get("status", "unresolved"),
            "summary": item.get("summary", "")[:300],
        })
    plot_advancements = []
    for item in ensure_list(payload.get("plot_advancements")):
        if not isinstance(item, dict):
            continue
        plot_advancements.append({
            "thread_hint": item.get("thread_hint", "")[:120],
            "type": item.get("type", "other"),
            "summary": item.get("summary", "")[:300],
        })
    relationship_changes = []
    for item in ensure_list(payload.get("relationship_changes")):
        if not isinstance(item, dict):
            continue
        relationship_changes.append({
            "characters": normalize_character_list(item.get("characters")),
            "change": item.get("change", "stable"),
            "reason": item.get("reason", "")[:240],
        })
    highlight_signals_raw = payload.get("highlight_signals") if isinstance(payload.get("highlight_signals"), dict) else {}
    highlight_signals = {
        "dramatic_turn": int(highlight_signals_raw.get("dramatic_turn", 0) or 0),
        "emotion_release": int(highlight_signals_raw.get("emotion_release", 0) or 0),
        "reveal": int(highlight_signals_raw.get("reveal", 0) or 0),
        "conflict_resolution": int(highlight_signals_raw.get("conflict_resolution", 0) or 0),
        "relationship_reversal": int(highlight_signals_raw.get("relationship_reversal", 0) or 0),
        "comedic_peak": int(highlight_signals_raw.get("comedic_peak", 0) or 0),
    }
    key_quotes = []
    for item in ensure_list(payload.get("key_quotes")):
        if isinstance(item, dict):
            quote = (item.get("quote") or "").strip()
            if quote:
                key_quotes.append({"quote": quote[:120], "reason": (item.get("reason") or "")[:200]})
        elif isinstance(item, str) and item.strip():
            key_quotes.append({"quote": item.strip()[:120], "reason": ""})
    memory_events = []
    for idx, item in enumerate(ensure_list(payload.get("memory_events"))):
        if not isinstance(item, dict):
            continue
        summary = (item.get("summary") or "").strip()
        if not summary:
            continue
        event_key_hint = item.get("event_key_hint") or summary[:24]
        memory_events.append({
            "event_key": make_story_key(f"{scene_index+1}-{event_key_hint}-{idx+1}", "event"),
            "summary": summary[:300],
            "characters": normalize_character_list(item.get("characters") or characters),
            "event_type": item.get("event_type") or payload.get("event_type") or "other",
            "importance": max(1, min(5, int(item.get("importance", 3) or 3))),
            "callback_tags": ensure_list(item.get("callback_tags"))[:6],
            "thread_hint": (item.get("thread_hint") or "")[:120],
            "is_open_question": bool(item.get("is_open_question", False)),
        })
    if not memory_events and payload.get("summary"):
        memory_events.append({
            "event_key": make_story_key(f"{scene_index+1}-{payload.get('summary', '')[:24]}", "event"),
            "summary": payload.get("summary", "")[:300],
            "characters": characters,
            "event_type": payload.get("event_type", "other"),
            "importance": max(1, min(5, 2 + int(max(highlight_signals.values()) >= 4))),
            "callback_tags": [],
            "thread_hint": "",
            "is_open_question": False,
        })
    return {
        "scene_index": scene_index,
        "start_time": float(scene_meta["start_time"]),
        "end_time": float(scene_meta["end_time"]),
        "summary": (payload.get("summary") or "").strip()[:400],
        "characters": characters,
        "event_type": payload.get("event_type", "other"),
        "emotion_tags": ensure_list(payload.get("emotion_tags"))[:8],
        "relationship_changes": relationship_changes,
        "conflicts": conflicts,
        "plot_advancements": plot_advancements,
        "memory_events": memory_events,
        "highlight_signals": highlight_signals,
        "key_quotes": key_quotes,
    }


def build_scene_structuring_prompt(scene_index: int, total_scenes: int, scene_analysis: str, transcript: str) -> str:
    return (
        f"你正在为互动短剧系统抽取第 {scene_index + 1}/{total_scenes} 个片段的结构化剧情信息。\n"
        "请严格输出 JSON，不要输出 Markdown，不要解释。\n"
        "目标：提取可以用于跨集剧情记忆、高光识别和互动触发的字段。\n"
        "字段 schema:\n"
        "{"
        "\"summary\":\"\","
        "\"characters\":[\"\"],"
        "\"event_type\":\"conflict|reveal|decision|emotion|relationship|comedy|setup|payoff|other\","
        "\"emotion_tags\":[\"\"],"
        "\"relationship_changes\":[{\"characters\":[\"\"],\"change\":\"closer|rupture|reversal|reconciliation|stable\",\"reason\":\"\"}],"
        "\"conflicts\":[{\"thread_hint\":\"\",\"status\":\"introduced|escalated|unresolved|resolved\",\"summary\":\"\"}],"
        "\"plot_advancements\":[{\"thread_hint\":\"\",\"type\":\"foreshadow|callback|identity_reveal|misunderstanding|truth_exposed|decision|twist|emotion_release|other\",\"summary\":\"\"}],"
        "\"memory_events\":[{\"event_key_hint\":\"\",\"summary\":\"\",\"characters\":[\"\"],\"event_type\":\"\",\"importance\":3,\"callback_tags\":[\"\"],\"thread_hint\":\"\",\"is_open_question\":false}],"
        "\"highlight_signals\":{\"dramatic_turn\":0,\"emotion_release\":0,\"reveal\":0,\"conflict_resolution\":0,\"relationship_reversal\":0,\"comedic_peak\":0},"
        "\"key_quotes\":[{\"quote\":\"\",\"reason\":\"\"}]"
        "}\n"
        "注意：\n"
        "1. summary 控制在 120 字内。\n"
        "2. 如果出现伏笔、旧账回收、误会解除、身份揭露、关系逆转、情绪爆发，一定体现在 plot_advancements 或 conflicts 中。\n"
        "3. 若信息不足，字段保留空数组或 other，不要杜撰。\n"
        f"\n场景分析：{scene_analysis}\n"
        f"\n字幕/转写：{transcript or '无'}"
    )


def structure_scene_story_memory(model, tokenizer, scene: Dict[str, Any], scene_index: int, total_scenes: int, scene_analysis: str, transcript: str) -> Dict[str, Any]:
    prompt = build_scene_structuring_prompt(scene_index, total_scenes, scene_analysis, transcript)
    frame_seed = scene["frames"][:1] if scene.get("frames") else [Image.new('RGB', (64, 64), color='black')]
    payload = call_structured_chat(
        model,
        tokenizer,
        frame_seed,
        safe_temporal_ids(scene.get("temporal_ids", []), limit=len(frame_seed)),
        prompt,
        fallback={}
    )
    return normalize_scene_story_payload(payload, scene_index, scene["meta"])


def score_story_overlap(scene_memory: Dict[str, Any], event_like: Dict[str, Any]) -> float:
    current_chars = set(normalize_character_list(scene_memory.get("characters")))
    candidate_chars = set(normalize_character_list(event_like.get("characters")))
    char_overlap = len(current_chars & candidate_chars)
    current_tokens = set(tokenize_story_text(
        " ".join([
            scene_memory.get("summary", ""),
            scene_memory.get("event_type", ""),
            " ".join(ensure_list(scene_memory.get("emotion_tags"))),
            " ".join(item.get("summary", "") for item in ensure_list(scene_memory.get("plot_advancements"))),
        ])
    ))
    candidate_tokens = set(tokenize_story_text(
        " ".join([
            event_like.get("summary", ""),
            event_like.get("event_type", ""),
            event_like.get("plot_thread_key", "") or "",
            " ".join(ensure_list(event_like.get("payoff_tags"))),
        ])
    ))
    token_overlap = len(current_tokens & candidate_tokens)
    same_event_type = 1 if scene_memory.get("event_type") == event_like.get("event_type") else 0
    unresolved_bonus = 1.5 if event_like.get("is_open_question") or event_like.get("status") == "open" else 0.0
    importance_bonus = float(event_like.get("importance", event_like.get("priority", 3)) or 3) * 0.2
    return round(char_overlap * 2.0 + token_overlap * 0.7 + same_event_type * 0.8 + unresolved_bonus + importance_bonus, 3)


def build_memory_retrieval_context(series_key: str, episode_number: int, scene_memory: Dict[str, Any], working_memory_events: List[Dict[str, Any]], working_plot_threads: List[Dict[str, Any]]) -> Dict[str, Any]:
    persisted_events = StoryMemoryEvent.query.filter(
        StoryMemoryEvent.series_key == series_key,
        StoryMemoryEvent.episode_number < episode_number
    ).order_by(StoryMemoryEvent.episode_number.desc(), StoryMemoryEvent.id.desc()).all()
    persisted_threads = PlotThreadState.query.filter(
        PlotThreadState.series_key == series_key,
        PlotThreadState.episode_number < episode_number
    ).order_by(PlotThreadState.episode_number.desc(), PlotThreadState.id.desc()).all()

    event_pool = [event.to_dict() for event in persisted_events] + working_memory_events
    ranked_events = []
    for item in event_pool:
        score = score_story_overlap(scene_memory, item)
        if score <= 0:
            continue
        ranked_events.append({**item, "relevance_score": score})
    ranked_events.sort(key=lambda x: (x["relevance_score"], x.get("importance", 0), x.get("episode_number", 0)), reverse=True)

    deduped_threads: Dict[str, Dict[str, Any]] = {}
    for thread in [thread.to_dict() for thread in persisted_threads] + working_plot_threads:
        thread_key = thread.get("thread_key") or make_story_key(thread.get("title", ""), "thread")
        existing = deduped_threads.get(thread_key)
        if existing is None or int(thread.get("episode_number", 0) or 0) >= int(existing.get("episode_number", 0) or 0):
            deduped_threads[thread_key] = {**thread, "thread_key": thread_key}

    ranked_threads = []
    for thread in deduped_threads.values():
        score = score_story_overlap(
            scene_memory,
            {
                "summary": f"{thread.get('title', '')} {thread.get('description', '')} {thread.get('last_event_summary', '')}",
                "event_type": "thread",
                "characters": thread.get("related_characters", []),
                "plot_thread_key": thread.get("thread_key"),
                "is_open_question": thread.get("status") != "resolved",
                "importance": thread.get("priority", 3),
            }
        )
        if score <= 0:
            continue
        ranked_threads.append({**thread, "relevance_score": score})
    ranked_threads.sort(key=lambda x: (x["relevance_score"], x.get("priority", 0), x.get("episode_number", 0)), reverse=True)

    return {
        "related_previous_events": ranked_events[:5],
        "unresolved_plot_threads": [item for item in ranked_threads if item.get("status") != "resolved"][:5],
        "top_related_events": ranked_events[:3],
        "top_related_threads": ranked_threads[:3],
    }


def infer_resolved_plot_threads(scene_memory: Dict[str, Any], retrieval_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    resolved = []
    candidate_threads = retrieval_context.get("top_related_threads", [])
    scene_text = " ".join([
        scene_memory.get("summary", ""),
        " ".join(item.get("summary", "") for item in ensure_list(scene_memory.get("conflicts"))),
        " ".join(item.get("summary", "") for item in ensure_list(scene_memory.get("plot_advancements"))),
    ])
    for thread in candidate_threads:
        hint_text = f"{thread.get('title', '')} {thread.get('description', '')} {thread.get('last_event_summary', '')}"
        overlap = len(set(tokenize_story_text(scene_text)) & set(tokenize_story_text(hint_text)))
        conflict_resolved = any(item.get("status") == "resolved" for item in ensure_list(scene_memory.get("conflicts")))
        explicit_release = any(
            item.get("type") in {"truth_exposed", "identity_reveal", "emotion_release", "callback"}
            for item in ensure_list(scene_memory.get("plot_advancements"))
        )
        if overlap > 0 and (conflict_resolved or explicit_release):
            resolved.append({
                "thread_key": thread.get("thread_key"),
                "title": thread.get("title"),
                "status_before": thread.get("status"),
                "resolution_summary": scene_memory.get("summary", ""),
            })
    return resolved[:3]


def choose_payoff_type(scene_memory: Dict[str, Any], related_events: List[Dict[str, Any]], resolved_threads: List[Dict[str, Any]]) -> str:
    plot_types = [item.get("type") for item in ensure_list(scene_memory.get("plot_advancements"))]
    if "identity_reveal" in plot_types:
        return "identity_reveal"
    if "truth_exposed" in plot_types:
        return "misunderstanding_cleared"
    if resolved_threads:
        return "conflict_resolution"
    if any(change.get("change") in {"reversal", "reconciliation", "rupture"} for change in ensure_list(scene_memory.get("relationship_changes"))):
        return "relationship_reversal"
    if "emotion_release" in plot_types or scene_memory.get("highlight_signals", {}).get("emotion_release", 0) >= 4:
        return "emotion_release"
    if related_events:
        return "foreshadow_payoff"
    return "none"


def choose_highlight_type(scene_memory: Dict[str, Any], payoff_type: str) -> str:
    signals = scene_memory.get("highlight_signals", {})
    if payoff_type == "identity_reveal":
        return "身份揭露"
    if payoff_type == "misunderstanding_cleared":
        return "误会解除"
    if payoff_type == "conflict_resolution":
        return "冲突回收"
    if payoff_type == "relationship_reversal":
        return "关系反转"
    if signals.get("emotion_release", 0) >= 4:
        return "情绪释放"
    if signals.get("comedic_peak", 0) >= 4:
        return "喜剧爆点"
    if signals.get("dramatic_turn", 0) >= 4:
        return "剧情反转"
    return "剧情推进"


def choose_interaction_type(payoff_type: str, highlight_type: str) -> str:
    mapping = {
        "identity_reveal": "truth_reveal_vote",
        "misunderstanding_cleared": "emotion_resonance",
        "conflict_resolution": "next_step_choice",
        "relationship_reversal": "relationship_prediction",
        "emotion_release": "emotion_resonance",
        "foreshadow_payoff": "callback_quiz",
        "none": "bullet_comment",
    }
    return mapping.get(payoff_type, "bullet_comment" if highlight_type == "剧情推进" else "emotion_resonance")


def compute_payoff_score(scene_memory: Dict[str, Any], retrieval_context: Dict[str, Any], resolved_threads: List[Dict[str, Any]]) -> float:
    signals = scene_memory.get("highlight_signals", {})
    base = (
        signals.get("dramatic_turn", 0) * 0.9 +
        signals.get("emotion_release", 0) * 0.7 +
        signals.get("reveal", 0) * 0.8 +
        signals.get("conflict_resolution", 0) * 0.9 +
        signals.get("relationship_reversal", 0) * 0.8 +
        signals.get("comedic_peak", 0) * 0.5
    )
    related_events = retrieval_context.get("top_related_events", [])
    plot_types = [item.get("type") for item in ensure_list(scene_memory.get("plot_advancements"))]
    callback_bonus = 1.4 if related_events else 0.0
    resolution_bonus = min(2.0, len(resolved_threads) * 0.9)
    reveal_bonus = 1.5 if any(item in {"identity_reveal", "truth_exposed"} for item in plot_types) else 0.0
    emotion_bonus = 1.2 if "emotion_release" in plot_types and related_events else 0.0
    payoff_score = min(10.0, round(base + callback_bonus + resolution_bonus + reveal_bonus + emotion_bonus, 2))
    return payoff_score


def select_anchor_segment(scene_segments: List[Dict[str, Any]], scene_memory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not scene_segments:
        return None
    quote_candidates = [item.get("quote", "") for item in ensure_list(scene_memory.get("key_quotes")) if item.get("quote")]
    for quote in quote_candidates:
        for seg in scene_segments:
            if quote and quote[:10] in seg.get("text", ""):
                return seg
    summary_tokens = set(tokenize_story_text(scene_memory.get("summary", "")))
    best_seg = None
    best_score = -1
    for seg in scene_segments:
        seg_score = len(summary_tokens & set(tokenize_story_text(seg.get("text", ""))))
        if seg_score > best_score:
            best_score = seg_score
            best_seg = seg
    return best_seg or scene_segments[-1]


def compute_highlight_timing(scene_memory: Dict[str, Any], scene_segments: List[Dict[str, Any]], highlight_type: str) -> Dict[str, float]:
    start_time = float(scene_memory["start_time"])
    end_time = float(scene_memory["end_time"])
    duration = max(0.1, end_time - start_time)
    anchor_seg = select_anchor_segment(scene_segments, scene_memory)
    if anchor_seg:
        peak_time = min(end_time, max(start_time, float(anchor_seg["end"])))
        clip_start = max(start_time, float(anchor_seg["start"]) - 0.8)
        clip_end = min(end_time, float(anchor_seg["end"]) + 1.2)
    else:
        peak_ratio = 0.78 if highlight_type in {"身份揭露", "情绪释放", "关系反转"} else 0.6
        peak_time = start_time + duration * peak_ratio
        clip_start = max(start_time, peak_time - min(2.5, duration * 0.35))
        clip_end = min(end_time, peak_time + min(2.0, duration * 0.25))

    interaction_candidates = []
    if anchor_seg:
        interaction_candidates.append(float(anchor_seg["end"]))
    for idx, seg in enumerate(scene_segments[:-1]):
        gap = float(scene_segments[idx + 1]["start"]) - float(seg["end"])
        if gap >= 0.25:
            interaction_candidates.append(min(end_time, float(seg["end"]) + min(gap, 0.6)))
    interaction_candidates.extend([min(end_time, peak_time + 0.35), max(start_time, end_time - 0.12)])
    interaction_time = next((candidate for candidate in interaction_candidates if candidate >= peak_time - 0.15), end_time)

    return {
        "start_time": round(clip_start, 3),
        "end_time": round(max(clip_start, clip_end), 3),
        "peak_time": round(peak_time, 3),
        "interaction_time": round(min(end_time, interaction_time), 3),
    }


def build_trigger_reason(scene_memory: Dict[str, Any], payoff_type: str, related_events: List[Dict[str, Any]], resolved_threads: List[Dict[str, Any]]) -> str:
    pieces = []
    if related_events:
        event_titles = "；".join(item.get("summary", "")[:30] for item in related_events[:2] if item.get("summary"))
        pieces.append(f"当前片段与前文事件形成回收：{event_titles}")
    if resolved_threads:
        thread_titles = "；".join(item.get("title", "") for item in resolved_threads if item.get("title"))
        pieces.append(f"推动或解决了悬而未决的剧情线：{thread_titles}")
    if payoff_type == "identity_reveal":
        pieces.append("出现身份/真相揭露，具备明显高光爆点")
    elif payoff_type == "misunderstanding_cleared":
        pieces.append("误会被澄清，前置压抑得到释放")
    elif payoff_type == "relationship_reversal":
        pieces.append("人物关系发生逆转，适合触发观众判断或站队互动")
    elif payoff_type == "emotion_release":
        pieces.append("长期积累的情绪在此处集中释放")
    if not pieces:
        pieces.append(f"当前场景的戏剧信号较强：{scene_memory.get('summary', '')}")
    return "；".join(pieces)


def evaluate_scene_highlight(scene_memory: Dict[str, Any], retrieval_context: Dict[str, Any], scene_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    related_events = retrieval_context.get("top_related_events", [])
    resolved_threads = infer_resolved_plot_threads(scene_memory, retrieval_context)
    payoff_type = choose_payoff_type(scene_memory, related_events, resolved_threads)
    highlight_type = choose_highlight_type(scene_memory, payoff_type)
    payoff_score = compute_payoff_score(scene_memory, retrieval_context, resolved_threads)
    timing = compute_highlight_timing(scene_memory, scene_segments, highlight_type)
    interaction_type = choose_interaction_type(payoff_type, highlight_type)
    trigger_reason = build_trigger_reason(scene_memory, payoff_type, related_events, resolved_threads)
    return {
        **timing,
        "scene_index": scene_memory["scene_index"],
        "payoff_score": payoff_score,
        "highlight_type": highlight_type,
        "payoff_type": payoff_type,
        "related_previous_events": related_events,
        "resolved_plot_threads": resolved_threads,
        "trigger_reason": trigger_reason,
        "interaction_type": interaction_type,
        "is_highlight": payoff_score >= 5.5 or (payoff_score >= 4.5 and payoff_type != "none"),
    }


def build_episode_memory_prompt(scene_memories: List[Dict[str, Any]], highlights: List[Dict[str, Any]], full_transcript: str) -> str:
    scene_payload = json.dumps(scene_memories, ensure_ascii=False)
    highlight_payload = json.dumps(highlights, ensure_ascii=False)
    return (
        "你是短剧互动系统的剧情记忆整理器。请严格输出 JSON，不要输出 Markdown。\n"
        "请基于全剧本片段数据，总结一集可持久化的剧情记忆。\n"
        "JSON schema:\n"
        "{"
        "\"episode_summary\":\"\","
        "\"main_events\":[{\"summary\":\"\",\"characters\":[\"\"],\"event_type\":\"\",\"importance\":3}],"
        "\"character_states\":[{\"character\":\"\",\"state\":\"\",\"goal\":\"\",\"relationship_changes\":[\"\"],\"evidence\":\"\"}],"
        "\"plot_threads\":[{\"thread_key\":\"\",\"title\":\"\",\"description\":\"\",\"status\":\"open|advanced|resolved\",\"priority\":3,\"related_characters\":[\"\"],\"source_event_keys\":[\"\"],\"resolution_summary\":\"\"}],"
        "\"memory_events\":[{\"event_key\":\"\",\"summary\":\"\",\"characters\":[\"\"],\"event_type\":\"\",\"importance\":3,\"callback_tags\":[\"\"],\"thread_hint\":\"\",\"is_open_question\":false}]"
        "}\n"
        "要求：episode_summary 150 字内；main_events 保留最重要的 3-8 条；plot_threads 要体现未解决冲突和已回收伏笔。\n"
        f"\nscene_memories={scene_payload}\n"
        f"\nhighlights={highlight_payload}\n"
        f"\nfull_transcript={clip_text(full_transcript or '', 3500)}"
    )


def normalize_episode_story_payload(payload: Dict[str, Any], scene_memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload = payload or {}
    main_events = []
    for idx, item in enumerate(ensure_list(payload.get("main_events"))):
        if not isinstance(item, dict) or not item.get("summary"):
            continue
        main_events.append({
            "event_key": item.get("event_key") or make_story_key(f"episode-main-{idx+1}-{item.get('summary', '')[:20]}", "event"),
            "summary": item.get("summary", "")[:300],
            "characters": normalize_character_list(item.get("characters")),
            "event_type": item.get("event_type", "other"),
            "importance": max(1, min(5, int(item.get("importance", 3) or 3))),
        })
    character_states = []
    for item in ensure_list(payload.get("character_states")):
        if not isinstance(item, dict):
            continue
        character = (item.get("character") or "").strip()
        if not character:
            continue
        character_states.append({
            "character": character[:60],
            "state": (item.get("state") or "")[:180],
            "goal": (item.get("goal") or "")[:180],
            "relationship_changes": ensure_list(item.get("relationship_changes"))[:6],
            "evidence": (item.get("evidence") or "")[:220],
        })
    plot_threads = []
    for idx, item in enumerate(ensure_list(payload.get("plot_threads"))):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or item.get("thread_key") or "").strip()
        if not title:
            continue
        plot_threads.append({
            "thread_key": item.get("thread_key") or make_story_key(f"thread-{idx+1}-{title}", "thread"),
            "title": title[:120],
            "description": (item.get("description") or "")[:300],
            "status": item.get("status", "open"),
            "priority": max(1, min(5, int(item.get("priority", 3) or 3))),
            "related_characters": normalize_character_list(item.get("related_characters")),
            "source_event_keys": ensure_list(item.get("source_event_keys"))[:12],
            "resolution_summary": (item.get("resolution_summary") or "")[:240],
        })
    memory_events = []
    source_events = payload.get("memory_events") if ensure_list(payload.get("memory_events")) else []
    if not source_events:
        source_events = [event for scene in scene_memories for event in ensure_list(scene.get("memory_events"))]
    for idx, item in enumerate(ensure_list(source_events)):
        if not isinstance(item, dict) or not item.get("summary"):
            continue
        memory_events.append({
            "event_key": item.get("event_key") or make_story_key(f"episode-memory-{idx+1}-{item.get('summary', '')[:20]}", "event"),
            "summary": item.get("summary", "")[:300],
            "characters": normalize_character_list(item.get("characters")),
            "event_type": item.get("event_type", "other"),
            "importance": max(1, min(5, int(item.get("importance", 3) or 3))),
            "callback_tags": ensure_list(item.get("callback_tags"))[:6],
            "thread_hint": (item.get("thread_hint") or "")[:120],
            "is_open_question": bool(item.get("is_open_question", False)),
        })
    return {
        "episode_summary": (payload.get("episode_summary") or "")[:500],
        "main_events": dedupe_keep_order(main_events)[:8],
        "character_states": dedupe_keep_order(character_states)[:12],
        "plot_threads": dedupe_keep_order(plot_threads)[:12],
        "memory_events": dedupe_keep_order(memory_events)[:20],
    }


def build_episode_story_memory(model, tokenizer, scene_data: List[Dict[str, Any]], scene_memories: List[Dict[str, Any]], highlights: List[Dict[str, Any]], full_transcript: str) -> Dict[str, Any]:
    rep_frames = [scene["frames"][0] for scene in scene_data[:2] if scene.get("frames")]
    rep_frames = rep_frames or [Image.new('RGB', (64, 64), color='black')]
    rep_tids = [[i * 5 for i in range(len(rep_frames))]]
    prompt = build_episode_memory_prompt(scene_memories, highlights, full_transcript)
    payload = call_structured_chat(model, tokenizer, rep_frames, rep_tids, prompt, fallback={})
    return normalize_episode_story_payload(payload, scene_memories)


def get_scene_segments(asr_segments: List[Dict[str, Any]], start_time: float, end_time: float, margin: float = 0.1) -> List[Dict[str, Any]]:
    return [
        seg for seg in asr_segments
        if not (float(seg["end"]) < start_time - margin or float(seg["start"]) > end_time + margin)
    ]


def persist_episode_story_memory(series_context: Dict[str, Any], video_filename: str, episode_story: Dict[str, Any], scene_memories: List[Dict[str, Any]], highlights: List[Dict[str, Any]]) -> Dict[str, Any]:
    series = StorySeries.query.filter_by(series_key=series_context["series_key"]).first()
    if not series:
        series = StorySeries(
            series_key=series_context["series_key"],
            title=series_context["series_title"],
            metadata_json={}
        )
        db.session.add(series)
        db.session.flush()
    else:
        series.title = series_context["series_title"]

    episode = EpisodeMemory.query.filter_by(
        series_key=series_context["series_key"],
        episode_number=series_context["episode_number"]
    ).first()
    if not episode:
        episode = EpisodeMemory(
            series_id=series.id,
            series_key=series_context["series_key"],
            episode_number=series_context["episode_number"],
            video_filename=video_filename,
        )
        db.session.add(episode)
        db.session.flush()

    episode.series_id = series.id
    episode.video_filename = video_filename
    episode.episode_summary = episode_story.get("episode_summary", "")
    episode.main_events = episode_story.get("main_events", [])
    episode.character_states = episode_story.get("character_states", [])
    episode.plot_threads = episode_story.get("plot_threads", [])
    episode.memory_events = episode_story.get("memory_events", [])
    episode.scene_memories = scene_memories
    episode.highlights = highlights
    episode.raw_payload = {
        "scene_memories": scene_memories,
        "highlights": highlights,
    }
    db.session.flush()

    StoryMemoryEvent.query.filter_by(
        series_key=series_context["series_key"],
        episode_number=series_context["episode_number"]
    ).delete(synchronize_session=False)
    PlotThreadState.query.filter_by(
        series_key=series_context["series_key"],
        episode_number=series_context["episode_number"]
    ).delete(synchronize_session=False)

    all_memory_events = []
    for scene_memory in scene_memories:
        for event in ensure_list(scene_memory.get("memory_events")):
            all_memory_events.append({
                **event,
                "scene_index": scene_memory.get("scene_index"),
                "start_time": scene_memory.get("start_time"),
                "end_time": scene_memory.get("end_time"),
            })
    all_memory_events.extend(episode_story.get("memory_events", []))
    deduped_memory_events = []
    seen_event_keys = set()
    for event in all_memory_events:
        event_key = event.get("event_key") or make_story_key(event.get("summary", ""), "event")
        if event_key in seen_event_keys:
            continue
        seen_event_keys.add(event_key)
        deduped_memory_events.append({**event, "event_key": event_key})

    for idx, event in enumerate(deduped_memory_events):
        db.session.add(StoryMemoryEvent(
            series_id=series.id,
            series_key=series_context["series_key"],
            episode_id=episode.id,
            episode_number=series_context["episode_number"],
            scene_index=event.get("scene_index"),
            start_time=event.get("start_time"),
            end_time=event.get("end_time"),
            event_key=event.get("event_key") or make_story_key(f"persisted-{idx+1}", "event"),
            summary=event.get("summary", ""),
            event_type=event.get("event_type", "other"),
            characters=normalize_character_list(event.get("characters")),
            payoff_tags=ensure_list(event.get("callback_tags")),
            plot_thread_key=(event.get("thread_hint") or None),
            is_open_question=bool(event.get("is_open_question", False)),
            is_resolved=bool(event.get("is_resolved", False)),
            importance=max(1, min(5, int(event.get("importance", 3) or 3))),
            metadata_json={"source": "scene_or_episode_memory"},
        ))

    for thread in episode_story.get("plot_threads", []):
        db.session.add(PlotThreadState(
            series_id=series.id,
            series_key=series_context["series_key"],
            episode_id=episode.id,
            episode_number=series_context["episode_number"],
            thread_key=thread.get("thread_key") or make_story_key(thread.get("title", ""), "thread"),
            title=thread.get("title", ""),
            description=thread.get("description", ""),
            status=thread.get("status", "open"),
            priority=max(1, min(5, int(thread.get("priority", 3) or 3))),
            related_characters=normalize_character_list(thread.get("related_characters")),
            source_event_keys=ensure_list(thread.get("source_event_keys")),
            last_event_summary=thread.get("description", ""),
            resolution_summary=thread.get("resolution_summary", ""),
            metadata_json={"source": "episode_memory"},
        ))

    db.session.commit()
    return episode.to_dict()


def build_series_memory_view(series_key: str) -> Dict[str, Any]:
    series = StorySeries.query.filter_by(series_key=series_key).first()
    if not series:
        return {}
    episodes = EpisodeMemory.query.filter_by(series_key=series_key).order_by(EpisodeMemory.episode_number.asc()).all()
    threads = PlotThreadState.query.filter_by(series_key=series_key).order_by(PlotThreadState.episode_number.desc(), PlotThreadState.id.desc()).all()
    latest_threads: Dict[str, Dict[str, Any]] = {}
    for thread in threads:
        payload = thread.to_dict()
        if payload["thread_key"] not in latest_threads:
            latest_threads[payload["thread_key"]] = payload
    unresolved_threads = [item for item in latest_threads.values() if item.get("status") != "resolved"]
    recent_events = StoryMemoryEvent.query.filter_by(series_key=series_key).order_by(
        StoryMemoryEvent.episode_number.desc(), StoryMemoryEvent.id.desc()
    ).limit(20).all()
    return {
        "series": series.to_dict(),
        "episodes": [episode.to_dict() for episode in episodes],
        "unresolved_plot_threads": unresolved_threads,
        "recent_memory_events": [event.to_dict() for event in recent_events],
    }

def map_to_nearest_scale(values: np.ndarray, scale: np.ndarray) -> np.ndarray:
    tree = cKDTree(scale[:, None])
    _, indices = tree.query(values[:, None])
    return scale[indices]

def resize_safe(pil_img: Image.Image, max_side: int = 512) -> Image.Image:
    w, h = pil_img.size
    s = max(w, h)
    if s <= max_side:
        return pil_img
    r = max_side / float(s)
    return pil_img.resize((int(round(w * r)), int(round(h * r))), Image.BICUBIC)

def get_video_codec_info(video_path: str):
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', '-select_streams', 'v:0', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            if 'streams' in info and len(info['streams']) > 0:
                return info['streams'][0].get('codec_name', 'unknown')
    except Exception as e:
        print(f"获取视频编码信息失败: {e}")
    return 'unknown'

def convert_video_if_needed(video_path: str, codec: str) -> str:
    incompatible_codecs = ['av1', 'vp9', 'hevc']
    if codec.lower() not in incompatible_codecs:
        return video_path
    base, ext = os.path.splitext(video_path)
    converted_path = f"{base}_h264{ext}"
    try:
        print(f"检测到 {codec.upper()} 编码，正在转换为 H264...")
        cmd = ['ffmpeg', '-i', video_path, '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy', '-y', converted_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(converted_path):
            print("视频转换完成。")
            return converted_path
        else:
            print(f"转换失败，将尝试直接读取原视频。错误: {result.stderr}")
            return video_path
    except Exception as e:
        print(f"转换过程出错: {e}，将尝试直接读取原视频。")
        return video_path

def read_video_safe(video_path: str):
    try:
        vr = VideoReader(video_path, ctx=cpu(0))
        _ = vr[0]
        return vr, 'decord'
    except Exception as e:
        print(f"Decord 读取失败: {e}，尝试使用 OpenCV")
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")
        return cap, 'opencv'
    except Exception as e:
        raise RuntimeError(f"所有视频读取方法都失败了: {e}")

def get_video_frames_opencv(cap, frame_indices):
    frames = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(frame_rgb))
        else:
            frames.append(Image.new('RGB', (640, 480), color='black'))
    return frames

def detect_scenes(video_path: str, threshold: float = 27.0, use_adaptive: bool = False):
    video = open_video(video_path)
    scene_manager = SceneManager()
    detector = AdaptiveDetector() if use_adaptive else ContentDetector(threshold=threshold)
    scene_manager.add_detector(detector)
    scene_manager.detect_scenes(video, show_progress=False)
    scene_list = scene_manager.get_scene_list()
    return [(scene[0].frame_num, scene[1].frame_num) for scene in scene_list]

def asr_transcribe_full(asr_model, video_path: str, language: str, beam_size: int, vad_filter: bool):
    segments_out = []
    try:
        segments, info = asr_model.transcribe(
            video_path,
            language=(None if not language else language),
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=False,
        )
        for seg in segments:
            segments_out.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
        full_text = "".join(s["text"] for s in segments_out).strip()
        return segments_out, full_text, info
    except Exception as e:
        print(f"ASR 转写失败: {e}")
        return [], "", None

def ocr_transcribe_subtitles(
    ocr_model,
    video_path: str,
    sample_fps: float = OCR_SAMPLE_FPS_DEFAULT,
    bottom_ratio: float = OCR_BOTTOM_RATIO_DEFAULT,
    text_score: float = OCR_TEXT_SCORE_DEFAULT,
):
    if ocr_model is None or sample_fps <= 0:
        return [], ""

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        print("警告: 无法打开视频进行字幕 OCR。")
        return [], ""

    native_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    native_fps = native_fps if native_fps > 0 else 25.0
    frame_interval = max(1, int(round(native_fps / sample_fps)))
    sampled_duration = 1.0 / sample_fps

    segments: List[Dict[str, Any]] = []
    frame_index = 0
    pending_text = ""
    pending_start = 0.0
    pending_end = 0.0
    pending_score = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % frame_interval != 0:
                frame_index += 1
                continue

            timestamp = frame_index / native_fps
            subtitle_crop = crop_subtitle_region(frame, bottom_ratio)
            ocr_result, _ = ocr_model(subtitle_crop, text_score=text_score)
            text_value, confidence = extract_ocr_text(ocr_result)
            if text_value:
                if pending_text and subtitle_similarity(pending_text, text_value) >= 0.86:
                    pending_end = timestamp + sampled_duration
                    pending_score = max(pending_score, confidence)
                else:
                    if pending_text:
                        segments.append(
                            {
                                "start": round(pending_start, 3),
                                "end": round(pending_end, 3),
                                "text": pending_text,
                                "source": "ocr",
                                "confidence": round(pending_score, 3),
                            }
                        )
                    pending_text = text_value
                    pending_start = timestamp
                    pending_end = timestamp + sampled_duration
                    pending_score = confidence
            elif pending_text:
                segments.append(
                    {
                        "start": round(pending_start, 3),
                        "end": round(pending_end, 3),
                        "text": pending_text,
                        "source": "ocr",
                        "confidence": round(pending_score, 3),
                    }
                )
                pending_text = ""
                pending_score = 0.0
            frame_index += 1
    finally:
        capture.release()

    if pending_text:
        segments.append(
            {
                "start": round(pending_start, 3),
                "end": round(pending_end, 3),
                "text": pending_text,
                "source": "ocr",
                "confidence": round(pending_score, 3),
            }
        )

    merged = merge_repeated_segments(segments)
    full_text = "".join(seg["text"] for seg in merged).strip()
    return merged, full_text


def timeline_text_per_scene(segments, scenes, margin: float = 0.15):
    scene_texts = []
    for (start_t, end_t) in scenes:
        pieces = [seg["text"] for seg in segments if not (seg["end"] < start_t - margin or seg["start"] > end_t + margin)]
        scene_texts.append("".join(pieces).strip())
    return scene_texts


def select_scene_transcripts(
    scene_times: List[Tuple[float, float]],
    ocr_segments: List[Dict[str, Any]],
    asr_segments: List[Dict[str, Any]],
):
    ocr_scene_texts = timeline_text_per_scene(ocr_segments, scene_times) if ocr_segments else [""] * len(scene_times)
    asr_scene_texts = timeline_text_per_scene(asr_segments, scene_times) if asr_segments else [""] * len(scene_times)
    chosen_texts = []
    chosen_sources = []
    for ocr_text, asr_text in zip(ocr_scene_texts, asr_scene_texts):
        normalized_ocr = normalize_subtitle_text(ocr_text)
        normalized_asr = normalize_subtitle_text(asr_text)
        if len(normalized_ocr) >= 4:
            chosen_texts.append(ocr_text)
            chosen_sources.append("ocr")
        elif normalized_asr:
            chosen_texts.append(asr_text)
            chosen_sources.append("asr")
        else:
            chosen_texts.append(ocr_text or asr_text)
            chosen_sources.append("ocr" if normalized_ocr else "asr")
    return chosen_texts, chosen_sources, ocr_scene_texts, asr_scene_texts


def fuse_transcript_segments(ocr_segments: List[Dict[str, Any]], asr_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not ocr_segments:
        return [dict(seg, source=seg.get("source", "asr")) for seg in asr_segments]
    fused = [dict(seg, source=seg.get("source", "ocr")) for seg in ocr_segments]
    for asr_segment in asr_segments:
        overlaps = [
            ocr_seg for ocr_seg in ocr_segments
            if min(asr_segment["end"], ocr_seg["end"]) - max(asr_segment["start"], ocr_seg["start"]) > 0.15
        ]
        if overlaps:
            continue
        fused.append(dict(asr_segment, source=asr_segment.get("source", "asr")))
    return merge_repeated_segments(fused, similarity_threshold=0.9)

def encode_video_by_scenes(video_path: str, scenes: List[Tuple[int, int]], choose_fps: float, max_side: int, time_scale: float):
    vr, method = read_video_safe(video_path)
    fps = float(vr.get_avg_fps()) if method == 'decord' else float(vr.get(cv2.CAP_PROP_FPS))
    total = len(vr) if method == 'decord' else int(vr.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps if fps > 0 else 0.0
    scene_data = []
    for scene_idx, (start_frame, end_frame) in enumerate(scenes):
        scene_length = end_frame - start_frame
        scene_duration = scene_length / fps if fps > 0 else 0.0
        need_frames = max(1, int(round(choose_fps * scene_duration)))
        scene_frame_idx = np.array([start_frame + int(round(i * (scene_length - 1) / max(1, need_frames - 1))) for i in range(need_frames)], dtype=np.int32)
        if method == 'decord':
            batch = vr.get_batch(scene_frame_idx).asnumpy()
            frames = [Image.fromarray(v.astype("uint8")).convert("RGB") for v in batch]
        else:
            frames = get_video_frames_opencv(vr, scene_frame_idx)
        frames = [resize_safe(im, max_side=max_side) for im in frames]
        ts = scene_frame_idx / fps if fps > 0 else np.linspace(start_frame / fps, end_frame / fps, num=len(scene_frame_idx), endpoint=False)
        grid = np.arange(0, max(duration, 1e-6), time_scale)
        ts_id = (map_to_nearest_scale(ts, grid) / time_scale).astype(np.int32)
        scene_meta = {"start_time": float(start_frame / fps), "end_time": float(end_frame / fps)}
        scene_data.append({"frames": frames, "temporal_ids": [ts_id.tolist()], "meta": scene_meta})
    if method == 'opencv':
        vr.release()
    overall_meta = {"fps": fps, "duration_sec": duration, "num_scenes": len(scenes), "total_picked_frames": sum(len(s["frames"]) for s in scene_data), "read_method": method}
    return scene_data, overall_meta

def call_chat(model, processor, frames, temporal_ids, prompt: str):
    if getattr(model, "_codex_standard_vlm", False):
        content = [{"type": "image", "image": frame} for frame in frames]
        content.append({"type": "text", "text": prompt})
        conversation = [{"role": "user", "content": content}]
        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        model_device = next(model.parameters()).device
        inputs = {
            key: value.to(model_device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
            )
        input_length = inputs["input_ids"].shape[1] if "input_ids" in inputs else 0
        generated_tokens = generated[:, input_length:] if input_length else generated
        decoded = processor.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return decoded[0].strip() if decoded else ""

    msgs = [{"role": "user", "content": frames + [prompt]}]
    with torch.inference_mode():
        out = model.chat(msgs=msgs, tokenizer=processor, use_image_id=False, max_slice_nums=1, temporal_ids=temporal_ids)
    return out[0] if isinstance(out, (list, tuple)) else out

def get_overall_story_digest(model, tokenizer, frames, tids, partials, overall_transcript_text="", scene_texts=None):
    scene_texts = scene_texts or []
    prompt = (
        "你将获得：（1）全片代表帧；（2）剧情单元分析；（3）完整转写文本。"
        "请输出一份面向短剧运营和互动设计的【全片剧情总览】。"
        "重点包括：主线推进、关键冲突、人物关系变化、情绪节奏、高光回收、适合互动的段落。"
        "避免任何审核、风险、违规、合规相关表述。\n\n"
        "请按以下结构输出：\n"
        "1. 整体剧情概括\n"
        "2. 人物与关系变化\n"
        "3. 情绪与节奏分布\n"
        "4. 高光与回收点总结\n"
        "5. 互动设计建议\n"
        "\n--- 剧情单元分析 ---\n" + "\n".join(partials) +
        ("\n\n--- 全文转写（截断或为空则忽略） ---\n" + (overall_transcript_text[:6000] + (" ……（已截断）" if len(overall_transcript_text) > 6000 else "")) if overall_transcript_text else "")
    )
    return call_chat(model, tokenizer, frames, tids, prompt).strip()

# 核心分析逻辑

def run_full_analysis(video_path, params):
    started_at = time.time()
    log_progress(f"开始分析视频: {video_path}")
    log_progress(f"使用参数: {params}")
    model, tokenizer, _model_dtype, asr_model, ocr_model = get_model_bundle()
    story_context = infer_story_context(params.get('videoFilename', os.path.basename(video_path)), params)
    use_scene = params.get('useSceneDetection', True)
    scene_thresh = params.get('sceneThreshold', 27.0)
    use_adaptive = params.get('useAdaptive', False)
    fps = params.get('chooseFps', 1.5)
    side = params.get('maxSide', 512)
    t_scale = params.get('timeScale', 0.1)
    prompt = params.get('promptText', "请分析这个场景")
    enable_asr = params.get('enableAsr', True)
    enable_ocr = params.get('enableOcr', True)
    asr_lang = params.get('asrLanguage', "")
    asr_beam = params.get('asrBeamSize', 5)
    asr_vad = params.get('asrVad', True)
    asr_max_chars = params.get('asrMaxChars', 1200)
    ocr_sample_fps = float(params.get('ocrSampleFps', OCR_SAMPLE_FPS_DEFAULT))
    ocr_bottom_ratio = float(params.get('ocrBottomRatio', OCR_BOTTOM_RATIO_DEFAULT))
    ocr_text_score = float(params.get('ocrTextScore', OCR_TEXT_SCORE_DEFAULT))
    asr_segments = []
    ocr_segments = []
    transcript_segments = []
    codec = get_video_codec_info(video_path)
    processed_video_path = convert_video_if_needed(video_path, codec)
    if use_scene:
        scenes = detect_scenes(processed_video_path, threshold=scene_thresh, use_adaptive=use_adaptive)
        if not scenes:
            log_progress("未检测到场景切换，将视频作为单一场景处理。")
            vr, _ = read_video_safe(processed_video_path)
            total_frames = len(vr) if isinstance(vr, VideoReader) else int(vr.get(cv2.CAP_PROP_FRAME_COUNT))
            scenes = [(0, total_frames)]
    else:
        vr, _ = read_video_safe(processed_video_path)
        total_frames = len(vr) if isinstance(vr, VideoReader) else int(vr.get(cv2.CAP_PROP_FRAME_COUNT))
        scenes = [(0, total_frames)]
    scene_data, meta = encode_video_by_scenes(processed_video_path, scenes, fps, side, t_scale)
    log_progress(f"切镜/抽帧完成: scenes={meta['num_scenes']}, frames={meta['total_picked_frames']}, duration={meta['duration_sec']:.2f}s")
    full_transcript, scene_transcripts = "", []
    scene_transcript_sources = ["none"] * len(scene_data)
    scene_times = [(s["meta"]["start_time"], s["meta"]["end_time"]) for s in scene_data]
    if enable_ocr and ocr_model:
        log_progress("开始字幕 OCR...")
        ocr_segments, ocr_full_text = ocr_transcribe_subtitles(
            ocr_model,
            processed_video_path,
            sample_fps=ocr_sample_fps,
            bottom_ratio=ocr_bottom_ratio,
            text_score=ocr_text_score,
        )
        log_progress(f"字幕 OCR 完成: segments={len(ocr_segments)}, transcript_chars={len(ocr_full_text)}")
    else:
        ocr_full_text = ""
    if enable_asr and asr_model:
        log_progress("开始语音转写...")
        asr_segments, asr_full_text, _ = asr_transcribe_full(asr_model, processed_video_path, asr_lang, asr_beam, asr_vad)
        log_progress(f"语音转写完成: segments={len(asr_segments)}, transcript_chars={len(asr_full_text)}")
    else:
        asr_full_text = ""
    if ocr_segments or asr_segments:
        scene_transcripts, scene_transcript_sources, ocr_scene_texts, asr_scene_texts = select_scene_transcripts(
            scene_times,
            ocr_segments,
            asr_segments,
        )
        transcript_segments = fuse_transcript_segments(ocr_segments, asr_segments)
        full_transcript = "".join(seg["text"] for seg in transcript_segments).strip()
    else:
        scene_transcripts = [""] * len(scene_data)
        ocr_scene_texts = [""] * len(scene_data)
        asr_scene_texts = [""] * len(scene_data)
    story_units = build_story_units(scene_data, scene_transcripts, params)
    focus_unit_indices = set(select_focus_units(story_units, params))
    log_progress(
        f"剧情单元切分完成: units={len(story_units)}, focus_units={len(focus_unit_indices)}, "
        f"target_duration={params.get('targetEventDurationSec', 18.0)}s"
    )
    log_progress("开始剧情单元分析...")
    partials = []
    structured_unit_memories = []
    highlight_candidates = []
    working_memory_events = []
    working_plot_threads = []
    max_frames_per_chunk = params.get('maxFramesPerChunk', 30)
    max_focus_frames = int(params.get("maxFocusFrames", max_frames_per_chunk))
    max_context_frames = int(params.get("maxContextFrames", max(8, min(16, max_frames_per_chunk // 2 or 8))))

    for unit in story_units:
        unit_started_at = time.time()
        transcript = unit["transcript"]
        is_focus_unit = unit["unit_index"] in focus_unit_indices
        sampled_frames, sampled_temporal_ids = sample_story_unit_frames(
            unit,
            scene_data,
            max_focus_frames if is_focus_unit else max_context_frames,
        )
        short_transcript = clip_text(transcript, asr_max_chars)
        log_progress(
            f"[剧情单元 {unit['unit_index']+1}/{len(story_units)}] 开始: {unit['start_time']:.1f}s - {unit['end_time']:.1f}s, "
            f"scenes={unit['scene_count']}, frames={len(sampled_frames)}, focus={is_focus_unit}, transcript_chars={len(short_transcript)}"
        )
        unit_prompt = build_story_unit_analysis_prompt(unit, short_transcript, prompt, is_focus_unit)
        unit_payload = {
            "frames": sampled_frames,
            "temporal_ids": sampled_temporal_ids,
            "meta": {"start_time": unit["start_time"], "end_time": unit["end_time"]},
        }
        part = analyze_scene_in_chunks(model, tokenizer, unit_payload, unit_prompt, max_frames_per_chunk)
        partials.append(part)
        unit_memory = structure_scene_story_memory(
            model,
            tokenizer,
            unit_payload,
            unit["unit_index"],
            len(story_units),
            part,
            short_transcript,
        )
        unit_memory["scene_indices"] = unit["scene_indices"]
        unit_memory["scene_count"] = unit["scene_count"]
        unit_memory["coarse_score"] = unit["coarse_score"]
        unit_memory["is_focus_unit"] = is_focus_unit
        retrieval_context = build_memory_retrieval_context(
            story_context["series_key"],
            story_context["episode_number"],
            unit_memory,
            working_memory_events,
            working_plot_threads
        )
        scene_segments = get_scene_segments(transcript_segments, unit_memory["start_time"], unit_memory["end_time"])
        highlight_payload = evaluate_scene_highlight(unit_memory, retrieval_context, scene_segments)
        unit_memory["memory_retrieval"] = {
            "related_previous_events": retrieval_context.get("related_previous_events", []),
            "unresolved_plot_threads": retrieval_context.get("unresolved_plot_threads", []),
        }
        unit_memory["highlight"] = highlight_payload
        structured_unit_memories.append(unit_memory)
        if highlight_payload.get("is_highlight"):
            highlight_candidates.append(highlight_payload)
        for memory_event in unit_memory.get("memory_events", []):
            working_memory_events.append({
                **memory_event,
                "episode_number": story_context["episode_number"],
                "scene_index": unit_memory["scene_index"],
                "start_time": unit_memory["start_time"],
                "end_time": unit_memory["end_time"],
            })
        for conflict in unit_memory.get("conflicts", []):
            if not conflict.get("thread_hint"):
                continue
            working_plot_threads.append({
                "thread_key": make_story_key(conflict["thread_hint"], "thread"),
                "title": conflict["thread_hint"],
                "description": conflict.get("summary", ""),
                "status": "resolved" if conflict.get("status") == "resolved" else "open",
                "priority": 3,
                "related_characters": unit_memory.get("characters", []),
                "source_event_keys": [item.get("event_key") for item in unit_memory.get("memory_events", []) if item.get("event_key")],
                "last_event_summary": unit_memory.get("summary", ""),
                "episode_number": story_context["episode_number"],
            })
        log_progress(
            f"[剧情单元 {unit['unit_index']+1}/{len(story_units)}] 完成: highlight={highlight_payload.get('highlight_type', '-')}, "
            f"payoff={highlight_payload.get('payoff_score', '-')}, elapsed={time.time() - unit_started_at:.1f}s"
        )
    log_progress("生成总报告...")
    rep_frames = []
    for unit in story_units[:3]:
        sampled_frames, _ = sample_story_unit_frames(unit, scene_data, 1)
        if sampled_frames:
            rep_frames.append(sampled_frames[0])
    rep_frames = rep_frames or [Image.new('RGB', (64, 64), color='black')]
    rep_tids = [[i*5 for i in range(len(rep_frames))]]
    overall_story_digest = get_overall_story_digest(model, tokenizer, rep_frames, rep_tids, partials, full_transcript, scene_transcripts)
    log_progress("剧情总览生成完成，开始汇总剧情记忆...")
    episode_story_memory = build_episode_story_memory(model, tokenizer, scene_data, structured_unit_memories, highlight_candidates, full_transcript)
    persisted_episode_memory = persist_episode_story_memory(
        story_context,
        params.get('videoFilename', os.path.basename(video_path)),
        episode_story_memory,
        structured_unit_memories,
        highlight_candidates
    )
    scene_details = [{
        "title": f"剧情单元 {i+1}",
        "time": f"{unit['start_time']:.2f}s - {unit['end_time']:.2f}s",
        "analysis": p,
        "transcript": unit["transcript"],
        "transcript_source": dedupe_keep_order([scene_transcript_sources[idx] for idx in unit["scene_indices"]]),
        "ocr_transcript": "".join(ocr_scene_texts[idx] for idx in unit["scene_indices"]).strip(),
        "asr_transcript": "".join(asr_scene_texts[idx] for idx in unit["scene_indices"]).strip(),
        "story_memory": structured_unit_memories[i],
        "memory_retrieval": structured_unit_memories[i].get("memory_retrieval", {}),
        "highlight": structured_unit_memories[i].get("highlight", {}),
        "scene_indices": unit["scene_indices"],
        "scene_count": unit["scene_count"],
        "coarse_score": unit["coarse_score"],
        "is_focus_unit": i in focus_unit_indices,
    } for i, (unit, p) in enumerate(zip(story_units, partials))]
    final_result = {
        "stats": {
            "scenes": meta['num_scenes'],
            "story_units": len(story_units),
            "focus_units": len(focus_unit_indices),
            "frames": meta['total_picked_frames'],
            "duration": f"{meta['duration_sec']:.2f}s",
            "fps": f"{meta['fps']:.2f}",
        },
        "pipeline": {
            "mode": "hierarchical_story_units",
            "unit_count": len(story_units),
            "focus_unit_indices": sorted(focus_unit_indices),
        },
        "story_context": story_context,
        "story_digest": overall_story_digest,
        "full_transcript": full_transcript,
        "transcript_pipeline": {
            "mode": "ocr_preferred_asr_fallback",
            "ocr_segments": len(ocr_segments),
            "asr_segments": len(asr_segments),
            "fused_segments": len(transcript_segments),
            "scene_sources": scene_transcript_sources,
        },
        "scene_details": scene_details,
        "story_units": scene_details,
        "story_memory": persisted_episode_memory,
        "highlights": highlight_candidates
    }
    if processed_video_path != video_path and os.path.exists(processed_video_path):
        os.remove(processed_video_path)
    log_progress(
        f"分析完成: scenes={meta['num_scenes']}, highlights={len(highlight_candidates)}, total_elapsed={time.time() - started_at:.1f}s"
    )
    return final_result

def download_video(video_url: str, download_folder: str) -> Dict[str, Any]:
    print(f"收到下载请求，URL: {video_url}")
    os.makedirs(download_folder, exist_ok=True)
    output_template = os.path.join(download_folder, "%(title)s.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
    }
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        downloaded_file_path = ydl.prepare_filename(info_dict)

    print(f"视频下载成功: {downloaded_file_path}")
    return {
        "message": "下载成功",
        "filename": os.path.basename(downloaded_file_path),
        "original_title": info_dict.get("title", "N/A"),
    }


def record_analysis_log(user_ip: str, video_filename: str, results: Dict[str, Any]) -> AnalysisLog:
    story_context = results.get("story_context", {})
    story_memory = results.get("story_memory", {})
    new_log = AnalysisLog(
        user_ip=user_ip,
        video_filename=video_filename,
        series_key=story_context.get("series_key"),
        episode_number=story_context.get("episode_number"),
        has_violations=False,
        report_summary=story_memory.get("episode_summary") or results.get("story_digest", "")[:500],
    )
    db.session.add(new_log)
    db.session.commit()
    print(f"新记录已存入数据库: ID={new_log.id}, IP={user_ip}, 文件名='{video_filename}'")
    return new_log


def list_analysis_logs(page: int, per_page: int) -> Dict[str, Any]:
    pagination = AnalysisLog.query.order_by(AnalysisLog.timestamp.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return {
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
        "logs": [log.to_dict() for log in pagination.items],
    }
