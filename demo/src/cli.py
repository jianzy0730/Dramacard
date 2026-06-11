from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch_runner import analyze_dataset
from .choice_point_builder import build_drama_choice_points
from .comfy_card_exporter import export_comfy_card_workflows
from .comfy_client import submit_comfy_workflows, sync_comfy_inputs
from .config import load_settings
from .drama_highlight_reporter import build_drama_highlight_report
from .ending_comic_builder import build_drama_ending_comics
from .ending_comic_prompt_exporter import export_drama_ending_prompts
from .pipeline import analyze


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-story-analyzer",
        description="OCR-first MP4 drama analyzer. Generates JSON outputs for downstream services.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a video file.")
    analyze_parser.add_argument("video", help="Input mp4 video path.")
    analyze_parser.add_argument("--output", required=True, help="Output directory.")
    analyze_parser.add_argument("--language", default="zh", help="Timeline/report language metadata.")
    analyze_parser.add_argument("--fps", type=float, default=3.0, help="First-pass OCR frame rate.")
    analyze_parser.add_argument("--refine-fps", type=float, default=10.0, help="Boundary refinement frame rate.")
    analyze_parser.add_argument(
        "--subtitle-crop",
        default="bottom",
        choices=["bottom", "full", "custom"],
        help="OCR crop mode. bottom uses the lower 35%% of the frame.",
    )
    analyze_parser.add_argument(
        "--crop-y-start",
        type=float,
        default=None,
        help="Custom crop start as 0-1 fraction of frame height. Used with --subtitle-crop custom.",
    )
    analyze_parser.add_argument(
        "--crop-y-end",
        type=float,
        default=None,
        help="Custom crop end as 0-1 fraction of frame height. Used with --subtitle-crop custom.",
    )
    analyze_parser.add_argument(
        "--previous-summary",
        default=None,
        help="Deprecated alias for --previous-memory.",
    )
    analyze_parser.add_argument(
        "--previous-memory",
        default=None,
        help="Optional previous series_memory.json path for cross-episode context.",
    )
    analyze_parser.add_argument("--llm-model", default=None, help="LLM model override.")
    analyze_parser.add_argument("--skip-llm", action="store_true", help="Skip LLM story_analysis.json generation.")
    analyze_parser.add_argument(
        "--skip-refine",
        action="store_true",
        help="Skip high-fps OCR boundary refinement.",
    )
    analyze_parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep extracted frame images and refine frame images. Default is cleanup after analysis.",
    )

    dataset_parser = subparsers.add_parser("analyze-dataset", help="Analyze all episodes in a dataset directory.")
    dataset_parser.add_argument("dataset_dir", help="Directory containing drama subfolders with episode videos.")
    dataset_parser.add_argument("--output", required=True, help="Output root directory.")
    dataset_parser.add_argument("--language", default="zh", help="Timeline/report language metadata.")
    dataset_parser.add_argument("--fps", type=float, default=3.0, help="First-pass OCR frame rate.")
    dataset_parser.add_argument("--refine-fps", type=float, default=10.0, help="Boundary refinement frame rate.")
    dataset_parser.add_argument(
        "--subtitle-crop",
        default="bottom",
        choices=["bottom", "full", "custom"],
        help="OCR crop mode. bottom uses the lower 35%% of the frame.",
    )
    dataset_parser.add_argument("--crop-y-start", type=float, default=None, help="Custom crop start 0-1.")
    dataset_parser.add_argument("--crop-y-end", type=float, default=None, help="Custom crop end 0-1.")
    dataset_parser.add_argument("--llm-model", default=None, help="LLM model override.")
    dataset_parser.add_argument("--skip-llm", action="store_true", help="Skip LLM story_analysis.json generation.")
    dataset_parser.add_argument("--skip-refine", action="store_true", help="Skip high-fps OCR boundary refinement.")
    dataset_parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep extracted frame images and refine frame images. Default is cleanup after analysis.",
    )
    dataset_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip episodes whose story_analysis.json already exists.",
    )

    drama_highlight_parser = subparsers.add_parser(
        "build-drama-highlights",
        help="Aggregate one drama's episode outputs into a ranked highlight report and keyframes.",
    )
    drama_highlight_parser.add_argument(
        "--drama-output",
        required=True,
        help="Directory containing one drama's episode output folders with story_analysis.json files.",
    )
    drama_highlight_parser.add_argument(
        "--drama-videos",
        required=True,
        help="Directory containing one drama's source episode videos.",
    )
    drama_highlight_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the drama highlight report and keyframes.",
    )
    drama_highlight_parser.add_argument(
        "--max-highlights",
        type=int,
        default=None,
        help="Maximum number of ranked highlights to keep. Defaults to a sparse series-level setting.",
    )
    drama_highlight_parser.add_argument(
        "--min-episode-gap",
        type=int,
        default=2,
        help="Minimum episode gap between selected highlights. Default keeps highlights sparse across episodes.",
    )
    drama_highlight_parser.add_argument(
        "--per-episode-limit",
        type=int,
        default=1,
        help="Maximum selected highlights per episode. Default is 1.",
    )
    drama_highlight_parser.add_argument(
        "--min-score",
        type=int,
        default=72,
        help="Minimum score required for a highlight to enter the final series-level report.",
    )

    drama_choice_parser = subparsers.add_parser(
        "build-choice-points",
        help="Backfill one drama's episode outputs with per-episode choice_points.json files.",
    )
    drama_choice_parser.add_argument(
        "--drama-output",
        required=True,
        help="Directory containing one drama's episode output folders with timeline/story_analysis files.",
    )
    drama_choice_parser.add_argument("--llm-model", default=None, help="LLM model override.")

    drama_endings_parser = subparsers.add_parser(
        "build-ending-comics",
        help="Generate 2x2 ending comic sheets from per-episode choice_points.json files.",
    )
    drama_endings_parser.add_argument(
        "--drama-output",
        required=True,
        help="Directory containing one drama's episode output folders with choice_points.json files.",
    )
    drama_endings_parser.add_argument(
        "--drama-videos",
        required=True,
        help="Directory containing one drama's source episode videos.",
    )
    drama_endings_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for ending comic images and manifest.",
    )

    drama_endings_prompt_parser = subparsers.add_parser(
        "export-ending-prompts",
        help="Export per-episode AI image prompts for ending comics.",
    )
    drama_endings_prompt_parser.add_argument(
        "--drama-output",
        required=True,
        help="Directory containing one drama's episode output folders with choice_points.json files.",
    )
    drama_endings_prompt_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for prompt bundles and manifest.",
    )

    comfy_export_parser = subparsers.add_parser(
        "export-comfy-card-workflows",
        help="Export ComfyUI card-generation workflows from a drama_highlight_report.json file.",
    )
    comfy_export_parser.add_argument(
        "--report",
        required=True,
        help="Path to drama_highlight_report.json.",
    )
    comfy_export_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for contact sheets, workflows, and manifest.",
    )
    comfy_export_parser.add_argument(
        "--workflow-template",
        default=str(Path(__file__).resolve().parents[1] / "assets" / "comfy" / "qwen_image_edit_card_template.json"),
        help="Path to the ComfyUI workflow template JSON.",
    )
    comfy_export_parser.add_argument(
        "--load-image-node",
        default="78",
        help="Node id of the LoadImage node in the workflow template.",
    )
    comfy_export_parser.add_argument(
        "--prompt-node",
        default="435",
        help="Node id of the prompt text node in the workflow template.",
    )
    comfy_export_parser.add_argument(
        "--save-image-node",
        default="60",
        help="Node id of the SaveImage node in the workflow template.",
    )

    comfy_sync_parser = subparsers.add_parser(
        "sync-comfy-inputs",
        help="Copy exported card contact sheets into a ComfyUI input directory.",
    )
    comfy_sync_parser.add_argument(
        "--manifest",
        required=True,
        help="Path to comfy_card_manifest.json.",
    )
    comfy_sync_parser.add_argument(
        "--comfy-input-dir",
        required=True,
        help="ComfyUI input directory path.",
    )

    comfy_submit_parser = subparsers.add_parser(
        "submit-comfy-workflows",
        help="Submit exported ComfyUI workflows to a running ComfyUI server.",
    )
    comfy_submit_parser.add_argument(
        "--manifest",
        required=True,
        help="Path to comfy_card_manifest.json.",
    )
    comfy_submit_parser.add_argument(
        "--server",
        default="http://127.0.0.1:8188",
        help="ComfyUI server URL.",
    )
    comfy_submit_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for how many workflows to submit.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        result = analyze(
            video_path=Path(args.video),
            output_dir=Path(args.output),
            language=args.language,
            fps=args.fps,
            refine_fps=args.refine_fps,
            subtitle_crop=args.subtitle_crop,
            crop_y_start=args.crop_y_start,
            crop_y_end=args.crop_y_end,
            previous_memory_path=Path(args.previous_memory or args.previous_summary)
            if (args.previous_memory or args.previous_summary)
            else None,
            llm_model=args.llm_model,
            skip_llm=args.skip_llm,
            skip_refine=args.skip_refine,
            keep_artifacts=args.keep_artifacts,
        )
        print(f"timeline: {result['timeline_path']}")
        if result["analysis_path"]:
            print(f"analysis: {result['analysis_path']}")
        if result["summary_path"]:
            print(f"summary:  {result['summary_path']}")
        if result["series_memory_path"]:
            print(f"memory:   {result['series_memory_path']}")
        if result["choice_points_path"]:
            print(f"choice:   {result['choice_points_path']}")
        print(f"report:   {result['report_path']}")
    elif args.command == "analyze-dataset":
        results = analyze_dataset(
            dataset_dir=Path(args.dataset_dir),
            output_root=Path(args.output),
            language=args.language,
            fps=args.fps,
            refine_fps=args.refine_fps,
            subtitle_crop=args.subtitle_crop,
            crop_y_start=args.crop_y_start,
            crop_y_end=args.crop_y_end,
            llm_model=args.llm_model,
            skip_llm=args.skip_llm,
            skip_refine=args.skip_refine,
            keep_artifacts=args.keep_artifacts,
            skip_existing=args.skip_existing,
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "build-drama-highlights":
        report = build_drama_highlight_report(
            drama_output_dir=Path(args.drama_output),
            drama_video_dir=Path(args.drama_videos),
            output_dir=Path(args.output),
            max_highlights=args.max_highlights,
            min_episode_gap=args.min_episode_gap,
            per_episode_limit=args.per_episode_limit,
            min_score=args.min_score,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "build-choice-points":
        report = build_drama_choice_points(
            drama_output_dir=Path(args.drama_output),
            settings=load_settings(),
            model=args.llm_model,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "build-ending-comics":
        report = build_drama_ending_comics(
            drama_output_dir=Path(args.drama_output),
            drama_video_dir=Path(args.drama_videos),
            output_dir=Path(args.output),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "export-ending-prompts":
        report = export_drama_ending_prompts(
            drama_output_dir=Path(args.drama_output),
            output_dir=Path(args.output),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "export-comfy-card-workflows":
        report = export_comfy_card_workflows(
            report_path=Path(args.report),
            output_dir=Path(args.output),
            workflow_template_path=Path(args.workflow_template),
            load_image_node_id=args.load_image_node,
            prompt_node_id=args.prompt_node,
            save_image_node_id=args.save_image_node,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "sync-comfy-inputs":
        report = sync_comfy_inputs(
            manifest_path=Path(args.manifest),
            comfy_input_dir=Path(args.comfy_input_dir),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "submit-comfy-workflows":
        report = submit_comfy_workflows(
            manifest_path=Path(args.manifest),
            server_url=args.server,
            limit=args.limit,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
