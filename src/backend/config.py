import json
from pathlib import Path
import sys
from typing import Optional, Dict, Any

def save_config(updates: dict) -> bool:
    global _config_cache
    config_path = get_config_path()
    current = load_config()
    current.update(updates)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        _config_cache = current
        return True
    except IOError as e:
        print(f"Ошибка записи конфига: {e}")
        return False

CONFIG_FILENAME = "settings.json"
_config_cache: Optional[Dict[str, Any]] = None

def get_config_path() -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / CONFIG_FILENAME

def _defaults() -> Dict[str, Any]:
    return {
        "ocr_path": "",
        "language": "rus+eng",
        "ocr_storage_enabled": False,
        "templates": [],
        "selected_template_index": -1,
        "scan_profiles": [],
    }

def load_config(force_reload: bool = False) -> dict:
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache

    config_path = get_config_path()
    defaults = _defaults()

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for key, val in defaults.items():
                if key not in data:
                    data[key] = val
            _config_cache = data
            return data
        except (json.JSONDecodeError, IOError):
            print("Ошибка чтения конфига, используются значения по умолчанию.")
    
    _config_cache = defaults.copy()
    return _config_cache

def save_main_settings(ocr_path: str, language: str, ocr_storage_enabled: bool) -> bool:
    return save_config({
        "ocr_path": ocr_path,
        "language": language,
        "ocr_storage_enabled": ocr_storage_enabled
    })

def get_templates() -> list[dict]:
    config = load_config()
    templates = config.get("templates", [])
    if templates and isinstance(templates[0], str):
        new_templates = []
        for i, pattern in enumerate(templates):
            new_templates.append({
                "name": pattern,
                "pattern": pattern,
                "structure": None
            })
        templates = new_templates
        config["templates"] = templates
        save_config(config)
    return templates

def save_templates(templates: list[dict]) -> bool:
    config = load_config()
    config["templates"] = templates
    return save_config(config)

def get_template_structure(index: int) -> str | None:
    templates = get_templates()
    if 0 <= index < len(templates):
        return templates[index].get("structure")
    return None

def set_selected_template_index(index: int) -> bool:
    return save_config({"selected_template_index": index})

def get_templates() -> list:
    return load_config().get("templates", [])

def get_selected_template_index() -> int:
    return load_config().get("selected_template_index", -1)

def id_to_lang_string(id_val: int) -> str:
    mapping = {0: "rus+eng", 1: "rus", 2: "eng"}
    return mapping.get(id_val, "rus+eng")

def lang_to_id(lang_str: str) -> int:
    mapping = {"rus+eng": 0, "rus": 1, "eng": 2}
    return mapping.get(lang_str, 0)

def get_scan_profiles() -> list:
    return load_config().get("scan_profiles", [])

def save_scan_profiles(profiles: list) -> bool:
    return save_config({"scan_profiles": profiles})

def reload_config() -> dict:
    return load_config(force_reload=True)