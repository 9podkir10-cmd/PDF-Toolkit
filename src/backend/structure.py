import json
import re
import shutil
from pathlib import Path
from typing import Dict, List

def sanitize_segment(segment: str) -> str:
    """Очищает сегмент пути от недопустимых символов."""
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s\-]', '', segment)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def build_path_from_structure(structure_template: str, zone_texts: List[str]) -> Path:
    """
    Подставляет значения zone_texts в шаблон структуры и возвращает относительный путь.
    Пример: structure_template = "{zone0}/{zone1}", zone_texts = ["ООО Ромашка", "2025"] → Path("ООО Ромашка/2025")
    """
    path_str = structure_template
    for i, text in enumerate(zone_texts):
        path_str = path_str.replace(f"{{zone{i}}}", text)
    # Разбиваем по '/' и очищаем каждый сегмент
    segments = [sanitize_segment(s) for s in path_str.split('/') if s.strip()]
    return Path(*segments)

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

        # Используем новое поле used_structure и zone_texts
        structure_template = ocr.get('used_structure')
        zone_texts = ocr.get('zone_texts', [])
        if not structure_template or not zone_texts:
            # Нет шаблона структуры или текстов — пропускаем
            continue

        try:
            rel_path = build_path_from_structure(structure_template, zone_texts)
        except Exception as e:
            details.append(f"Ошибка построения пути для {key}: {e}")
            errors += 1
            continue

        if not rel_path.parts:
            # Пустой путь — некуда перемещать
            details.append(f"Пустой путь для {key}, пропускаем")
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

        target_dir = base_dir / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / source_file.name

        try:
            shutil.move(str(source_file), str(target_file))
            moved += 1
            entry['structured'] = True
            entry['moved_to'] = target_file.relative_to(base_dir).as_posix()
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
            structure_template = ocr.get('used_structure')
            zone_texts = ocr.get('zone_texts', [])
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

    # Построение дерева каталогов
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