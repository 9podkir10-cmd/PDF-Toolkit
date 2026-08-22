import json
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

def find_manifest(pdf_path: Path) -> Optional[Path]:
    """
    Ищет файл manifest.json в папке, где находится PDF,
    или в соседней папке с суффиксом _hardlink.
    """
    current_dir = pdf_path.parent

    # 1. Проверяем текущую папку
    manifest_path = current_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path

    # 2. Проверяем папку <текущая_папка>_hardlink в родительской директории
    parent_dir = current_dir.parent
    hardlink_dir = parent_dir / (current_dir.name + "_hardlink")
    manifest_path = hardlink_dir / "manifest.json"
    if hardlink_dir.exists() and manifest_path.exists():
        return manifest_path

    return None


def update_manifest_for_file(
    manifest_path: Path,
    file_path: Path,          # путь к файлу ДО переименования
    ocr_info: Dict[str, Any]
) -> bool:
    """
    Обновляет запись в манифесте, соответствующую file_path.
    ocr_info должен содержать ключи:
        - is_recognized: bool
        - new_name: str (новое имя файла, только имя, без пути)
        - used_template: str | None (шаблон, если применялся)
    Возвращает True, если запись найдена и обновлена.
    """
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception:
        return False

    # Определяем стратегию поиска записи
    found = False

    # Если файл лежит в той же папке, что и манифест (скорее всего output_dir),
    # ищем по имени файла (ключ в манифесте)
    if file_path.parent == manifest_path.parent:
        key = file_path.name
        if key in manifest.get('unique', {}):
            manifest['unique'][key]['ocr'] = ocr_info
            found = True
        elif key in manifest.get('duplicates', {}):
            manifest['duplicates'][key]['ocr'] = ocr_info
            found = True
    else:
        # Иначе ищем по original_path (файл в source_dir)
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

    # Сохраняем обновлённый манифест
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return True


def sanitize_segment(segment: str) -> str:
    """
    Очищает сегмент пути от недопустимых символов.
    Оставляет только буквы, цифры, пробелы и дефис.
    """
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

def update_manifest_after_structure(manifest_path: Path, file_key: str, new_path: str):
    """
    Обновляет запись в манифесте, добавляя поля structured и moved_to.
    """
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception:
        return False

    # Ищем запись в unique или duplicates по ключу (имя файла в папке вывода)
    for section in ('unique', 'duplicates'):
        if file_key in manifest.get(section, {}):
            manifest[section][file_key]['structured'] = True
            manifest[section][file_key]['moved_to'] = new_path
            break
    else:
        # Если ключ не найден, пробуем искать по original_path? Но для структуризации мы работаем с файлами в выводной папке,
        # и ключ — это имя файла, так что он должен быть.
        return False

    # Сохраняем обновлённый манифест
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return True

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

        # Проверяем, не структурирован ли уже (можно добавить опционально)
        if entry.get('structured', False):
            continue

        template = ocr.get('used_template')
        if not template:
            continue

        segments = extract_path_segments_from_template(template)
        if not segments:
            continue

        # Исходный файл – используем new_name из ocr, либо ключ
        source_name = ocr.get('new_name')
        if source_name:
            source_file = base_dir / source_name
        else:
            source_file = base_dir / key

        if not source_file.exists():
            errors += 1
            details.append(f"Файл не найден: {source_file}")
            continue

        # Строим целевой путь
        target_dir = base_dir
        for seg in segments:
            target_dir = target_dir / seg
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / source_file.name

        try:
            shutil.move(str(source_file), str(target_file))
            moved += 1
            # Обновляем запись в манифесте
            entry['structured'] = True
            # Относительный путь с прямыми слешами
            rel_path = target_file.relative_to(base_dir).as_posix()
            entry['moved_to'] = rel_path
            details.append(f"Перемещён: {source_file.name} → {target_file}")
        except Exception as e:
            errors += 1
            details.append(f"Ошибка перемещения {source_file.name}: {str(e)}")

    # Сохраняем обновлённый манифест
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "moved": moved,
        "errors": errors,
        "details": details
    }
    
def preview_structure(base_dir: Path) -> str:
    """
    Анализирует манифест и строит дерево папок, которые будут созданы
    при структуризации (для файлов с is_recognized и ещё не structured).
    Возвращает текстовое представление дерева с количеством файлов в каждой папке.
    """
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        return "manifest.json не найден"

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Собираем все относительные пути для файлов, которые будут перемещены
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
            # Строим путь как строку с разделителями '/'
            rel_path = '/'.join(segments)
            paths.append(rel_path)

    if not paths:
        return "Нет файлов для структуризации (все уже обработаны или нет распознанных)."

    # Строим дерево папок с подсчётом файлов в каждой конечной папке
    tree = {}
    for path in paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        # Увеличиваем счётчик файлов в этой папке
        current['__files__'] = current.get('__files__', 0) + 1

    # Рекурсивная функция вывода дерева
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