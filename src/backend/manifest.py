import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from backend.manifest_center import ManifestCenter

def find_manifest(pdf_path: Path) -> Optional[Path]:
    current_dir = pdf_path.parent

    manifest_path = current_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    
    parent_dir = current_dir.parent
    hardlink_dir = parent_dir / (current_dir.name + "_hardlink")
    manifest_path = hardlink_dir / "manifest.json"
    if hardlink_dir.exists() and manifest_path.exists():
        return manifest_path
    
    return None

def update_manifest_for_file(manifest_path: Path, file_path: Path, ocr_info: Dict[str, Any]) -> bool:
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception:
        return False

    found = False

    if file_path.parent == manifest_path.parent:
        key = file_path.name
        if key in manifest.get('unique', {}):
            manifest['unique'][key]['ocr'] = ocr_info
            found = True
        elif key in manifest.get('duplicates', {}):
            manifest['duplicates'][key]['ocr'] = ocr_info
            found = True
    else:
        file_path_str = str(file_path)
        for section in ('unique', 'duplicates'):
            for key, entry in manifest.get(section, {}).items():
                if entry.get('original_path') == file_path_str:
                    entry['ocr'] = ocr_info
                    found = True
                    break
            if found:
                break

    if not found:
        return False

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return True

def update_manifest_after_structure(manifest_path: Path, file_key: str, new_path: str):
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception:
        return False

    for section in ('unique', 'duplicates'):
        if file_key in manifest.get(section, {}):
            manifest[section][file_key]['structured'] = True
            manifest[section][file_key]['moved_to'] = new_path
            break
    else:
        return False

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return True

def load_manifest(path):
    path = Path(path)

    if path.is_dir():
        return ManifestCenter.for_folder(path).load()

    return ManifestCenter(path).load()

def is_ocr_recognized(manifest: Dict[str, Any], filename: str) -> bool:

    entry = manifest.get('unique', {}).get(filename)
    if not entry:
        entry = manifest.get('duplicates', {}).get(filename)
    if not entry:
        return False
    ocr = entry.get('ocr', {})
    return ocr.get('is_recognized', False)