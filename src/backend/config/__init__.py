import sys
from pathlib import Path
from .repository import ConfigRepository
from .service import ConfigService

CONFIG_FILENAME = "settings.json"
_config_service_instance = None

def get_config_path() -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / CONFIG_FILENAME


def get_config_service() -> ConfigService:
    global _config_service_instance
    if _config_service_instance is None:
        path = get_config_path()
        repo = ConfigRepository(path)
        _config_service_instance = ConfigService(repo)
    return _config_service_instance