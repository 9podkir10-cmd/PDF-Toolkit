import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from filelock import FileLock
from .models import Manifest

class ManifestRepository:
    def __init__(self, path: Path):
        self._path = path
        self._lock = FileLock(str(path) + ".lock")

    def load(self) -> Manifest:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Manifest(**data)
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {self._path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid manifest JSON: {e}")

    def save(self, manifest: Manifest) -> None:
        with self._lock:
            manifest.updated_at = datetime.now()
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2, ensure_ascii=False, default=str)

    def exists(self) -> bool:
        return self._path.exists()