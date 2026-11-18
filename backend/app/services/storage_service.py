"""Private file storage abstraction.

Milestone 1 uses the local filesystem. The interface (save / open_path / delete) is kept small so that a
private cloud object-storage backend can replace it later without touching callers.
"""
import os
import uuid
from pathlib import Path

from app.config import settings


class StorageError(Exception):
    pass


class LocalStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        path = (self.base_dir / storage_key).resolve()
        # Path traversal guard: the resolved path must stay inside base_dir.
        if self.base_dir != path and self.base_dir not in path.parents:
            raise StorageError("Invalid storage key")
        return path

    def save(self, patient_id: uuid.UUID, extension: str, content: bytes) -> str:
        """Store bytes under a server-generated name and return the storage key."""
        folder = f"patient_{patient_id.hex}"
        key = f"{folder}/{uuid.uuid4().hex}{extension}"
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        with open(tmp, "wb") as fh:
            fh.write(content)
        os.replace(tmp, path)
        return key

    def open_path(self, storage_key: str) -> Path:
        path = self._resolve(storage_key)
        if not path.is_file():
            raise StorageError("File not found")
        return path

    def delete(self, storage_key: str) -> None:
        try:
            self._resolve(storage_key).unlink(missing_ok=True)
        except StorageError:
            pass


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(settings.storage_dir)
    return _storage
