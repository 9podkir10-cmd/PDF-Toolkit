
from .models import Config, ScanProfile, Template
from .repository import ConfigRepository


class ConfigService:
    def __init__(self, repo: ConfigRepository):
        self._repo = repo
        self._config: Config | None = None

    def _load(self) -> Config:
        if self._config is None:
            self._config = self._repo.load()
        return self._config

    def _save(self) -> bool:
        if self._config is None:
            return False
        return self._repo.save(self._config)

    def get_ocr_path(self) -> str:
        return self._load().ocr_path

    def get_language(self) -> str:
        return self._load().language

    def is_ocr_storage_enabled(self) -> bool:
        return self._load().ocr_storage_enabled

    def update_main_settings(self, ocr_path: str, language: str, ocr_storage_enabled: bool) -> bool:
        config = self._load()
        config.ocr_path = ocr_path
        config.language = language
        config.ocr_storage_enabled = ocr_storage_enabled
        return self._save()

    def get_templates(self) -> list[Template]:
        return self._load().templates

    def get_selected_template_index(self) -> int:
        return self._load().selected_template_index

    def set_selected_template_index(self, index: int) -> bool:
        config = self._load()
        config.selected_template_index = index
        return self._save()

    def save_templates(self, templates: list[Template]) -> bool:
        config = self._load()
        config.templates = templates
        return self._save()

    def get_scan_profiles(self) -> list[ScanProfile]:
        return self._load().scan_profiles

    def save_scan_profiles(self, profiles: list[ScanProfile]) -> bool:
        config = self._load()
        config.scan_profiles = profiles
        return self._save()

    def reload(self) -> None:
        self._config = self._repo.load()
        
    def get_config(self) -> Config:
        return self._load()