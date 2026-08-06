import json
import os
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
        "language": "ruseng"
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "language" not in data or "ocr_path" not in data:
                    return defaults
                return data
        except (json.JSONDecodeError, IOError):
            print("Ошибка чтения конфига, используются значения по умолчанию.")
            return defaults
    
    return defaults

def save_config(ocr_path: str, language: str) -> bool:
    config_path = get_config_path()
    data = {
        "ocr_path": ocr_path,
        "language": language
    }
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Ошибка записи конфига: {e}")
        return False

def id_to_lang_string(id_val: int) -> str:
    mapping = {
        0: "ruseng",
        1: "rus",
        2: "eng"
    }
    return mapping.get(id_val, "ruseng")
