from pathlib import Path
import json
from typing import Dict, Any, List, Optional

def get_folder_stats(folder_path: str) -> Dict[str, Any]:
    """
    Возвращает статистику для одной папки на основе её manifest.json.
    Структура manifest:
        stats.total         - общее количество PDF
        stats.unique        - количество уникальных файлов
        stats.duplicates    - количество дубликатов
        stats.errors        - количество ошибок
        unique              - словарь {имя_файла: {ocr: {is_recognized, new_name, used_template}}}
    """
    base = Path(folder_path)
    if not base.is_dir():
        return {"error": "Папка не существует"}

    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        # Возвращаем признак отсутствия манифеста, но не считаем ошибкой
        return {
            "has_manifest": False,
            "total": 0,
            "recognized": 0,
            "remaining": 0,
            "percent": 0.0,
            "unique": 0,
            "duplicates": 0,
            "errors": 0,
            "files": []
        }

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        return {"error": f"Ошибка чтения manifest.json: {e}"}

    stats = manifest.get("stats", {})
    total = stats.get("total", 0)
    unique_count = stats.get("unique", 0)
    duplicates = stats.get("duplicates", 0)
    errors = stats.get("errors", 0)

    unique_files = manifest.get("unique", {})
    recognized_count = 0
    file_list = []

    for filename, entry in unique_files.items():
        ocr = entry.get("ocr", {})
        is_rec = ocr.get("is_recognized", False)
        if is_rec:
            recognized_count += 1
        file_list.append({
            "filename": filename,
            "is_recognized": is_rec,
            "new_name": ocr.get("new_name"),
            "used_template": ocr.get("used_template")
        })

    remaining = total - recognized_count
    percent = (recognized_count / total * 100) if total > 0 else 0.0

    return {
        "has_manifest": True,
        "total": total,
        "recognized": recognized_count,
        "remaining": remaining,
        "percent": round(percent, 2),
        "unique": unique_count,
        "duplicates": duplicates,
        "errors": errors,
        "files": file_list
    }


def get_dashboard_stats_for_root(root_path: str) -> Dict[str, Any]:
    """
    Сканирует все подпапки первого уровня внутри root_path,
    для каждой с manifest.json вычисляет статистику,
    и возвращает общую сводку + список по папкам.
    Папки без manifest.json игнорируются.
    """
    root = Path(root_path)
    if not root.is_dir():
        return {"error": "Корневая папка не существует"}

    subdirs = [d for d in root.iterdir() if d.is_dir()]

    folder_stats_list = []
    total_pdfs = 0
    total_recognized = 0
    total_duplicates = 0
    total_errors = 0

    for sub in subdirs:
        stats = get_folder_stats(str(sub))
        if "error" in stats:
            continue  # пропускаем проблемные папки (ошибка чтения)
        # Пропускаем папки без манифеста
        if not stats.get("has_manifest", False):
            continue
        stats["folder_name"] = sub.name
        folder_stats_list.append(stats)
        total_pdfs += stats["total"]
        total_recognized += stats["recognized"]
        total_duplicates += stats.get("duplicates", 0)
        total_errors += stats.get("errors", 0)

    total_remaining = total_pdfs - total_recognized
    overall_percent = (total_recognized / total_pdfs * 100) if total_pdfs > 0 else 0.0

    return {
        "total_folders": len(folder_stats_list),
        "total_pdfs": total_pdfs,
        "total_recognized": total_recognized,
        "total_remaining": total_remaining,
        "total_duplicates": total_duplicates,
        "total_errors": total_errors,
        "overall_percent": round(overall_percent, 2),
        "folders": folder_stats_list
    }