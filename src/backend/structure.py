import json
import re
import shutil
from pathlib import Path
from typing import Dict, List

def sanitize_segment(segment: str) -> str:
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s\-]', '', segment)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def extract_path_segments_from_template(template: str) -> List[str]:
    if not template:
        return []
    parts = re.split(r'\{zone\d+\}', template)
    result = []
    for part in parts:
        cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s\-]', '', part)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            result.append(cleaned)
    return result

def structure_pdfs(base_dir: Path) -> Dict:
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        return {"error": "manifest.json не найден в выбранной папке"}

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    moved = 0
    errors = 0
    details = []

    all_entries = {}
    for section in ('unique', 'duplicates'):
        for key, entry in manifest.get(section, {}).items():
            all_entries[key] = entry

    for key, entry in all_entries.items():
        ocr = entry.get('ocr')
        if not ocr or not ocr.get('is_recognized'):
            continue

        if entry.get('structured', False):
            continue

        template = ocr.get('used_template')
        if not template:
            continue

        segments = extract_path_segments_from_template(template)
        if not segments:
            continue

        source_name = ocr.get('new_name')
        if source_name:
            source_file = base_dir / source_name
        else:
            source_file = base_dir / key

        if not source_file.exists():
            errors += 1
            details.append(f"Файл не найден: {source_file}")
            continue

        target_dir = base_dir
        for seg in segments:
            target_dir = target_dir / seg
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / source_file.name

        try:
            shutil.move(str(source_file), str(target_file))
            moved += 1
            entry['structured'] = True
            rel_path = target_file.relative_to(base_dir).as_posix()
            entry['moved_to'] = rel_path
            details.append(f"Перемещён: {source_file.name} → {target_file}")
        except Exception as e:
            errors += 1
            details.append(f"Ошибка перемещения {source_file.name}: {str(e)}")

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "moved": moved,
        "errors": errors,
        "details": details
    }
    
def preview_structure(base_dir: Path) -> str:
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        return "manifest.json не найден"

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    paths = []
    for section in ('unique', 'duplicates'):
        for key, entry in manifest.get(section, {}).items():
            if entry.get('structured'):
                continue
            ocr = entry.get('ocr')
            if not ocr or not ocr.get('is_recognized'):
                continue
            template = ocr.get('used_template')
            if not template:
                continue
            segments = extract_path_segments_from_template(template)
            if not segments:
                continue
            rel_path = '/'.join(segments)
            paths.append(rel_path)

    if not paths:
        return "Нет файлов для структуризации (все уже обработаны или нет распознанных)."

    tree = {}
    for path in paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        current['__files__'] = current.get('__files__', 0) + 1

    def render_tree(node, indent=0):
        lines = []
        items = sorted([k for k in node.keys() if k != '__files__'])
        for i, key in enumerate(items):
            is_last = (i == len(items) - 1)
            prefix = "    " * indent + ("└── " if is_last else "├── ")
            count = node[key].get('__files__', 0)
            line = f"{prefix}{key}/ ({count} files)" if count else f"{prefix}{key}/"
            lines.append(line)
            sub_lines = render_tree(node[key], indent + 1)
            lines.extend(sub_lines)
        return lines

    return "\n".join(render_tree(tree))