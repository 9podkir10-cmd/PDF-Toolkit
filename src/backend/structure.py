import re
import shutil
from pathlib import Path
from typing import Dict, List
from backend.manifest import get_manifest_service

def sanitize_segment(segment: str) -> str:
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s\-]', '', segment)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def build_path_from_structure(structure_template: str, zone_texts: List[str]) -> Path:
    path_str = structure_template
    for i, text in enumerate(zone_texts):
        path_str = path_str.replace(f"{{zone{i}}}", text)
    segments = [sanitize_segment(s) for s in path_str.split('/') if s.strip()]
    return Path(*segments)

def structure_pdfs(base_dir: Path, pending_ids: List[str]) -> Dict:
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        return {"error": "manifest.json не найден в выбранной папке"}

    service = get_manifest_service(str(manifest_path))
    manifest = service.load()
    if manifest is None:
        return {"error": "Не удалось загрузить манифест"}

    moved = 0
    errors = 0
    details = []

    for record_id in pending_ids:
        record = service.get_record(record_id)
        if record is None:
            errors += 1
            details.append(f"Запись с ID {record_id} не найдена")
            continue

        if not record.ocr.is_recognized:
            continue
        if record.structure.structured:
            continue

        structure_template = record.structure.used_structure
        zone_texts = record.ocr.zone_texts

        if not structure_template or not zone_texts:
            continue

        try:
            rel_path = build_path_from_structure(structure_template, zone_texts)
        except Exception as e:
            details.append(f"Ошибка построения пути для {record.filename}: {e}")
            errors += 1
            continue

        if not rel_path.parts:
            details.append(f"Пустой путь для {record.filename}, пропускаем")
            continue

        source_file = base_dir / record.filename
        if not source_file.exists():
            errors += 1
            details.append(f"Файл не найден: {source_file}")
            continue

        target_dir = base_dir / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / source_file.name

        try:
            shutil.move(str(source_file), str(target_file))
            moved += 1
            record.structure.structured = True
            record.structure.moved_to = target_file.relative_to(base_dir).as_posix()
            details.append(f"Перемещён: {source_file.name} → {target_file}")
        except Exception as e:
            errors += 1
            details.append(f"Ошибка перемещения {source_file.name}: {str(e)}")
   
    service.save()
    return {"moved": moved, "errors": errors, "details": details}

def preview_structure(base_dir: Path) -> str:
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        return "manifest.json не найден."

    service = get_manifest_service(str(manifest_path))
    manifest = service.load()
    if manifest is None:
        return "Не удалось загрузить манифест."

    paths = []
    for record in manifest.records.values():
        if record.structure.structured:
            continue
        if not record.ocr.is_recognized:
            continue
        structure_template = record.structure.used_structure
        zone_texts = record.ocr.zone_texts
        if not structure_template or not zone_texts:
            continue
        try:
            rel_path = build_path_from_structure(structure_template, zone_texts)
            if rel_path.parts:
                paths.append('/'.join(rel_path.parts))
        except Exception:
            pass

    if not paths:
        return "Нет файлов для структуризации (все уже обработаны или нет шаблона структуры)."

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