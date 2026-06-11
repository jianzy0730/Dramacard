from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .io_utils import load_json, save_json


def sync_comfy_inputs(manifest_path: Path, comfy_input_dir: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path.resolve())
    comfy_input_dir = comfy_input_dir.resolve()
    comfy_input_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []
    for item in manifest.get("items", []):
        source_path_str = item.get("contact_sheet_path")
        if not source_path_str:
            continue
        source_path = Path(str(source_path_str))
        if not source_path.exists():
            copied.append(
                {
                    "highlight_id": item.get("highlight_id", ""),
                    "status": "missing_source",
                    "source_path": str(source_path),
                }
            )
            continue
        target_path = comfy_input_dir / source_path.name
        shutil.copy2(source_path, target_path)
        copied.append(
            {
                "highlight_id": item.get("highlight_id", ""),
                "status": "copied",
                "source_path": str(source_path),
                "target_path": str(target_path),
            }
        )

    report = {
        "manifest_path": str(manifest_path.resolve()),
        "comfy_input_dir": str(comfy_input_dir),
        "copied_count": len([item for item in copied if item["status"] == "copied"]),
        "items": copied,
    }
    save_json(report, manifest_path.resolve().parent / "comfy_input_sync_report.json")
    return report


def submit_comfy_workflows(
    manifest_path: Path,
    server_url: str = "http://127.0.0.1:8188",
    limit: int | None = None,
) -> dict[str, Any]:
    manifest = load_json(manifest_path.resolve())
    normalized_url = server_url.rstrip("/")
    submitted: list[dict[str, Any]] = []
    items = list(manifest.get("items", []))
    if limit is not None:
        items = items[:limit]

    for item in items:
        workflow_path = item.get("workflow_path")
        if not workflow_path:
            submitted.append(
                {
                    "highlight_id": item.get("highlight_id", ""),
                    "status": "missing_workflow_path",
                }
            )
            continue
        payload = load_json(Path(str(workflow_path)))
        try:
            response = _post_json(
                url=f"{normalized_url}/prompt",
                payload={"prompt": payload},
            )
            submitted.append(
                {
                    "highlight_id": item.get("highlight_id", ""),
                    "status": "submitted",
                    "workflow_path": str(workflow_path),
                    "response": response,
                }
            )
        except RuntimeError as exc:
            submitted.append(
                {
                    "highlight_id": item.get("highlight_id", ""),
                    "status": "failed",
                    "workflow_path": str(workflow_path),
                    "error": str(exc),
                }
            )

    report = {
        "manifest_path": str(manifest_path.resolve()),
        "server_url": normalized_url,
        "submitted_count": len([item for item in submitted if item["status"] == "submitted"]),
        "items": submitted,
    }
    save_json(report, manifest_path.resolve().parent / "comfy_submit_report.json")
    return report


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection failed: {exc}") from exc
    return json.loads(content) if content else {}
