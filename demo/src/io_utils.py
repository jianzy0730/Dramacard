from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def prepare_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "frames").mkdir(parents=True, exist_ok=True)


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def cleanup_generated_images(output_dir: Path) -> None:
    for dirname in ["frames", "refine_frames"]:
        path = output_dir / dirname
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
