from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

import storage
from services.document_storage import DocumentStorage, get_document_storage, sanitize_filename

router = APIRouter()


def document_storage() -> DocumentStorage:
    try:
        return get_document_storage(storage.ROOT)
    except ValueError as e:
        raise HTTPException(500, str(e)) from e


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
    project = storage.load_project(slug)
    file_id = uuid.uuid4().hex[:12]
    original_filename = file.filename or "upload"
    mime_type = file.content_type or "application/octet-stream"
    store = document_storage()
    file.file.seek(0)
    stored = store.save(
        project_slug=slug,
        file_id=file_id,
        original_filename=original_filename,
        mime_type=mime_type,
        source=file.file,
    )

    record = {
        "id": file_id,
        "filename": stored.original_filename,
        "original_filename": stored.original_filename,
        "stored_path": stored.stored_path,
        "storage_backend": stored.storage_backend,
        "category": category,
        "mime_type": stored.mime_type,
        "size_bytes": stored.size_bytes,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    project.setdefault("uploaded_files", []).append(record)
    storage.save_project(slug, project)
    return record


@router.get("/{slug}/uploads/{file_id}")
def get_upload(slug: str, file_id: str) -> StreamingResponse:
    project = storage.load_project(slug)
    for f in project.get("uploaded_files", []):
        if f["id"] == file_id:
            store = document_storage()
            backend = f.get("storage_backend") or "local"
            if backend != store.backend_name:
                raise HTTPException(501, f"storage backend '{backend}' is not configured")
            stored_path = f.get("stored_path")
            if not stored_path or not store.exists(stored_path):
                raise HTTPException(404, "stored file not found")
            filename = f.get("original_filename") or f.get("filename") or "upload"
            quoted = quote(filename, safe="")
            safe_header = sanitize_filename(filename).replace('"', "")
            return StreamingResponse(
                store.iter_file(stored_path),
                media_type=f.get("mime_type", "application/octet-stream"),
                headers={
                    "content-disposition": (
                        f'attachment; filename="{safe_header}"; filename*=UTF-8\'\'{quoted}'
                    ),
                },
            )
    raise HTTPException(404, "upload not found")
