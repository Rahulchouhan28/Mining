from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

import storage
from services.extract import auto_prepare
from services.year_planner import generate_for_project

router = APIRouter()


@router.get("")
def list_all() -> list[dict[str, Any]]:
    return storage.list_projects()


@router.post("")
def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    name = payload.get("project_details", {}).get("project_name", "")
    if not name:
        raise HTTPException(400, "project_details.project_name is required")
    slug = storage.slugify(name)
    saved = storage.save_project(slug, payload)
    return {"slug": slug, **saved}


@router.get("/{slug}")
def get_project(slug: str) -> dict[str, Any]:
    try:
        return {"slug": slug, **storage.load_project(slug)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.put("/{slug}")
def update_project(slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    saved = storage.save_project(slug, payload)
    return {"slug": slug, **saved}


@router.delete("/{slug}")
def delete_project(slug: str) -> dict[str, str]:
    import shutil
    d = storage.project_dir(slug)
    shutil.rmtree(d, ignore_errors=True)
    return {"status": "deleted", "slug": slug}


@router.post("/{slug}/uploads")
async def upload_file(slug: str, category: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    import uuid
    from datetime import datetime, timezone

    project = storage.load_project(slug)
    target_dir = storage.project_dir(slug) / "uploads"
    safe_name = (file.filename or "upload").replace("/", "_").replace("\\", "_")
    file_id = uuid.uuid4().hex[:12]
    target = target_dir / f"{file_id}_{safe_name}"
    contents = await file.read()
    target.write_bytes(contents)

    record = {
        "id": file_id,
        "filename": safe_name,
        "stored_path": str(target.relative_to(storage.ROOT.parent)),
        "category": category,
        "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": len(contents),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    project.setdefault("uploaded_files", []).append(record)
    storage.save_project(slug, project)
    return record


ALL_ALTERNATIVES = [
    "base", "conservative", "aggressive",
    "low_waste", "environment_sensitive",
    "cost_optimized", "grade_blending", "minimum_disturbance",
]


@router.post("/{slug}/auto-prepare")
def auto_prepare_project(slug: str) -> dict[str, Any]:
    """Extract a lease boundary from uploaded vector files (or synthesize one
    from area_ha), seed engineering defaults, and run the year-wise generator
    for ALL 8 alternatives so every approach button is populated on Step 6 /
    Step 9. Per-alternative cherry-picking is done from Step 5 (Advanced).
    """
    try:
        project = auto_prepare(slug)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e

    project["selected_alternatives"] = list(ALL_ALTERNATIVES)
    result = generate_for_project(project, ALL_ALTERNATIVES)
    project["generated_plans"] = result["generated_plans"]
    project["quantity_tables"] = result["quantity_tables"]
    project["validation_warnings"] = result["validation_warnings"]
    storage.save_project(slug, project)

    lease_source = None
    for f in (project.get("digitized_layers") or {}).get("features") or []:
        if (f.get("properties") or {}).get("layer_type") == "lease_boundary":
            lease_source = (f.get("properties") or {}).get("source")
            break

    return {
        "slug": slug,
        "alternatives": list(ALL_ALTERNATIVES),
        "lease_source": lease_source,
        "plan_count": len(result["generated_plans"]),
        "warning_count": len(result["validation_warnings"]),
    }


@router.get("/{slug}/uploads/{file_id}")
def get_upload(slug: str, file_id: str) -> FileResponse:
    project = storage.load_project(slug)
    for f in project.get("uploaded_files", []):
        if f["id"] == file_id:
            path = storage.ROOT.parent / f["stored_path"]
            return FileResponse(path, media_type=f.get("mime_type", "application/octet-stream"), filename=f["filename"])
    raise HTTPException(404, "upload not found")
