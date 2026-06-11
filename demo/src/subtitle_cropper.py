from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CropConfig:
    mode: str = "bottom"
    y_start: float | None = None
    y_end: float | None = None


def crop_for_ocr(frame_path: Path, crop_config: CropConfig, output_path: Path | None = None) -> Path:
    if crop_config.mode == "full":
        return frame_path

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for subtitle cropping. Install Pillow or use --subtitle-crop full.") from exc

    image = Image.open(frame_path)
    width, height = image.size
    top_ratio, bottom_ratio = _crop_ratios(crop_config)
    top = int(height * top_ratio)
    bottom = int(height * bottom_ratio)
    if top < 0 or bottom > height or top >= bottom:
        raise ValueError("Invalid subtitle crop range. Use 0 <= y_start < y_end <= 1.")

    output_path = output_path or frame_path.with_name(f"{frame_path.stem}_subtitle{frame_path.suffix}")
    cropped = image.crop((0, top, width, bottom))
    cropped.save(output_path)
    return output_path


def _crop_ratios(crop_config: CropConfig) -> tuple[float, float]:
    if crop_config.mode == "bottom":
        return 0.65, 1.0
    if crop_config.mode == "custom":
        if crop_config.y_start is None or crop_config.y_end is None:
            raise ValueError("--crop-y-start and --crop-y-end are required when --subtitle-crop custom.")
        return crop_config.y_start, crop_config.y_end
    raise ValueError(f"Unsupported subtitle crop mode: {crop_config.mode}")
