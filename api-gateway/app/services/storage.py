"""
File storage utilities for report uploads.

Currently implements LOCAL storage with deterministic path structure:
reports/{participant_id}/{report_id}/original.docx
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path
from fastapi import UploadFile


class StorageError(Exception):
    """Base error for storage operations."""


class FileTooLargeError(StorageError):
    """Raised when uploaded file exceeds the configured size."""

    def __init__(self, max_bytes: int):
        super().__init__(f"File exceeds maximum allowed size of {max_bytes} bytes")
        self.max_bytes = max_bytes


@dataclass(slots=True)
class StoredFile:
    """Metadata for a stored file."""

    key: str
    path: Path
    size_bytes: int
    etag: str


class LocalReportStorage:
    """LOCAL storage backend for report files."""

    CHUNK_SIZE = 1024 * 1024  # 1 MiB

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def ensure_base(self) -> None:
        """Ensure base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def report_key(self, participant_id: str, report_id: str) -> str:
        """Build key for report original document."""
        return f"reports/{participant_id}/{report_id}/original.docx"

    def resolve_path(self, key: str) -> Path:
        """Resolve absolute path for storage key."""
        return self.base_path / key

    async def save_report(self, upload: UploadFile, key: str, max_bytes: int) -> StoredFile:
        """
        Persist uploaded report to disk.

        Args:
            upload: UploadFile from FastAPI request
            key: storage key relative to base directory
            max_bytes: maximum allowed file size

        Returns:
            StoredFile metadata with size and ETag hash.

        Raises:
            FileTooLargeError: If file exceeds size limit
            StorageError: On I/O problems
        """
        self.ensure_base()

        destination = self.resolve_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        hasher = hashlib.md5()
        total_size = 0

        try:
            with destination.open("wb") as sink:
                while True:
                    chunk = await upload.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        raise FileTooLargeError(max_bytes)
                    sink.write(chunk)
                    hasher.update(chunk)
        except FileTooLargeError:
            # Clean up partially written file
            destination.unlink(missing_ok=True)
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError(str(exc)) from exc
        finally:
            await upload.close()

        etag = hasher.hexdigest()
        return StoredFile(key=key, path=destination, size_bytes=total_size, etag=etag)

    async def compute_etag(self, path: Path) -> str:
        """Compute MD5-based ETag for an existing file."""

        def _hash_file() -> str:
            hasher = hashlib.md5()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(self.CHUNK_SIZE), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()

        return await asyncio.to_thread(_hash_file)

    def delete_file(self, path: Path) -> None:
        """Delete file if it exists (non-fatal)."""
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # Log warning in future when logging subsystem is ready
            pass
