import json
from pathlib import Path
from typing import Optional
from .models import Config


class ConfigRepository:
    def __init__(self, path: Path):
        self._path = path

    def load(self) -> Config:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config(**data)
        except FileNotFoundError:
            return Config()
        except json.JSONDecodeError:
            return Config()

    def save(self, config: Config) -> bool:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=4, ensure_ascii=False)
            return True
        except IOError:
            return False

    def exists(self) -> bool:
        return self._path.exists()