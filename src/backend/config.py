import json
from pathlib import Path
import sys

CONFIG_FILENAME = "settings.json"

def get_config_path() -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / CONFIG_FILENAME

def load_config() -> dict:
    config_path = get_config_path()
    defaults = {
        "ocr_path": "",
        "language": "rus+eng",
        "ocr_storage_enabled": False,
        "templates": [],
        "selected_template_index": -1
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, val in defaults.items():
                    if key not in data:
                        data[key] = val
                return data
        except (json.JSONDecodeError, IOError):
            print("Ошибка чтения конфига, используются значения по умолчанию.")
            return defaults
    return defaults

def save_config(updates: dict) -> bool:
    config_path = get_config_path()
    current = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                current = json.load(f)
        except:
            pass
    current.update(updates)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Ошибка записи конфига: {e}")
        return False

def save_main_settings(ocr_path: str, language: str, ocr_storage_enabled: bool) -> bool:
    return save_config({
        "ocr_path": ocr_path,
        "language": language,
        "ocr_storage_enabled": ocr_storage_enabled
    })

# Шаблоны
def save_templates(templates: list) -> bool:
    return save_config({"templates": templates})

def set_selected_template_index(index: int) -> bool:
    return save_config({"selected_template_index": index})

def get_templates() -> list:
    return load_config().get("templates", [])

def get_selected_template_index() -> int:
    return load_config().get("selected_template_index", -1)

def id_to_lang_string(id_val: int) -> str:
    mapping = {0: "rus+eng", 1: "rus", 2: "eng"}
    return mapping.get(id_val, "rus+eng")