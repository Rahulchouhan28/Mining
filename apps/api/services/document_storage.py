"""Document storage abstraction for uploaded project files.

The upload routes depend on the `DocumentStorage` protocol, not on local disk
details. Replacing `LocalDocumentStorage` with an S3/GCS/Azure implementation
later should only require changing the provider factory in the route layer.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import BinaryIO, Iterator, Protocol


CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class StoredDocument:
    file_id: str
    original_filename: str
    stored_path: str
    storage_backend: str
    mime_type: str
    size_bytes: int


class DocumentStorage(Protocol):
    backend_name: str

    def save(
        self,
        *,
        project_slug: str,
        file_id: str,
        original_filename: str,
        mime_type: str,
        source: BinaryIO,
    ) -> StoredDocument:
        """Persist `source` and return stable storage metadata."""

    def iter_file(self, stored_path: str, *, chunk_size: int = CHUNK_SIZE) -> Iterator[bytes]:
        """Yield file bytes for download/preview responses."""

    def exists(self, stored_path: str) -> bool:
        """Return whether `stored_path` is available in this backend."""


def sanitize_filename(filename: str | None) -> str:
    """Keep the user-visible name readable while removing path separators."""
    raw = (filename or "upload").strip() or "upload"
    return raw.replace("/", "_").replace("\\", "_")


class LocalDocumentStorage:
    backend_name = "local"

    def __init__(self, projects_root: Path):
        self.projects_root = projects_root
        self.workspace_root = projects_root.parent
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        *,
        project_slug: str,
        file_id: str,
        original_filename: str,
        mime_type: str,
        source: BinaryIO,
    ) -> StoredDocument:
        safe_name = sanitize_filename(original_filename)
        target_dir = self.projects_root / project_slug / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{file_id}_{safe_name}"

        size = 0
        with target.open("wb") as out:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
                size += len(chunk)

        return StoredDocument(
            file_id=file_id,
            original_filename=original_filename or "upload",
            stored_path=target.relative_to(self.workspace_root).as_posix(),
            storage_backend=self.backend_name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size,
        )

    def iter_file(self, stored_path: str, *, chunk_size: int = CHUNK_SIZE) -> Iterator[bytes]:
        path = self.resolve_path(stored_path)
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def exists(self, stored_path: str) -> bool:
        try:
            return self.resolve_path(stored_path).is_file()
        except ValueError:
            return False

    def resolve_path(self, stored_path: str) -> Path:
        normalized = stored_path.replace("\\", "/")
        path = (self.workspace_root / normalized).resolve()
        workspace = self.workspace_root.resolve()
        if path != workspace and workspace not in path.parents:
            raise ValueError("stored_path is outside the workspace")
        return path


def get_document_storage(projects_root: Path) -> DocumentStorage:
    """Return the configured document storage backend.

    Only local storage is implemented in this phase. Future cloud adapters can
    be selected here without changing upload routes or UI-facing contracts.
    """
    backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        return LocalDocumentStorage(projects_root)
    raise ValueError(f"Unsupported document storage backend: {backend}")
