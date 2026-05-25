"""On-disk project storage. v1 has no database — each project is a folder."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2] / "projects"
ROOT.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "untitled"


def project_dir(slug: str) -> Path:
    p = ROOT / slug
    p.mkdir(parents=True, exist_ok=True)
    (p / "uploads").mkdir(exist_ok=True)
    (p / "exports").mkdir(exist_ok=True)
    return p


def project_json_path(slug: str) -> Path:
    return project_dir(slug) / "project.json"


def load_project(slug: str) -> dict[str, Any]:
    path = project_json_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Project '{slug}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(slug: str, data: dict[str, Any]) -> dict[str, Any]:
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "created_at" not in data:
        data["created_at"] = data["updated_at"]
    path = project_json_path(slug)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def list_projects() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        meta_path = d / "project.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            out.append({
                "slug": d.name,
                "project_name": meta.get("project_details", {}).get("project_name", d.name),
                "updated_at": meta.get("updated_at"),
            })
        except Exception:  # noqa: BLE001 — keep listing resilient
            continue
    return out
