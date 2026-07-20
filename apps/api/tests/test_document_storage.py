from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes import projects  # noqa: E402
from services.document_storage import LocalDocumentStorage, sanitize_filename  # noqa: E402


def test_local_document_storage_preserves_metadata_and_streams_bytes(tmp_path: Path) -> None:
    store = LocalDocumentStorage(tmp_path / "projects")
    payload = b"stored document bytes"

    stored = store.save(
        project_slug="demo",
        file_id="abc123",
        original_filename="Surface Plan.pdf",
        mime_type="application/pdf",
        source=BytesIO(payload),
    )

    assert stored.file_id == "abc123"
    assert stored.original_filename == "Surface Plan.pdf"
    assert stored.storage_backend == "local"
    assert stored.mime_type == "application/pdf"
    assert stored.size_bytes == len(payload)
    assert stored.stored_path == "projects/demo/uploads/abc123_Surface Plan.pdf"
    assert b"".join(store.iter_file(stored.stored_path)) == payload


def test_local_document_storage_sanitizes_only_the_disk_object_name(tmp_path: Path) -> None:
    store = LocalDocumentStorage(tmp_path / "projects")
    stored = store.save(
        project_slug="demo",
        file_id="id1",
        original_filename="folder\\unsafe/name.pdf",
        mime_type="application/pdf",
        source=BytesIO(b"x"),
    )

    assert sanitize_filename("folder\\unsafe/name.pdf") == "folder_unsafe_name.pdf"
    assert stored.original_filename == "folder\\unsafe/name.pdf"
    assert stored.stored_path.endswith("id1_folder_unsafe_name.pdf")
    assert store.exists(stored.stored_path)


def test_auto_prepare_endpoint_is_storage_only(monkeypatch) -> None:
    project = {
        "project_details": {"project_name": "Storage Only", "area_ha": 4.8},
        "uploaded_files": [{"id": "doc1", "filename": "lease.kml"}],
        "digitized_layers": {"type": "FeatureCollection", "features": []},
        "selected_alternatives": ["base", "aggressive"],
        "generated_plans": [{"alternative": "base", "features": {"type": "FeatureCollection", "features": []}}],
        "quantity_tables": [{"alternative": "base", "rows": []}],
        "validation_warnings": [{"severity": "info", "code": "OLD", "message": "existing"}],
    }
    before = deepcopy(project)

    monkeypatch.setattr(projects.storage, "load_project", lambda slug: project)

    def forbidden_save(*_args, **_kwargs):
        raise AssertionError("auto-prepare should not mutate project storage")

    monkeypatch.setattr(projects.storage, "save_project", forbidden_save)

    result = projects.auto_prepare_project("demo")

    assert result == {
        "slug": "demo",
        "alternatives": ["base", "aggressive"],
        "lease_source": "document storage only",
        "plan_count": 0,
        "warning_count": 0,
    }
    assert project == before
