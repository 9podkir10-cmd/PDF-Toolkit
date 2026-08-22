from pathlib import Path
import json
from typing import Dict, Any

def get_dashboard_stats(folder_path: str) -> Dict[str, Any]:
    base = Path(folder_path)
    if not base.is_dir():
        return {"error": "Папка не существует"}

    all_pdfs = list(base.rglob("*.pdf"))
    total = len(all_pdfs)

    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        return {
            "total": total,
            "recognized": 0,
            "remaining": total,
            "percent": 0.0,
            "has_manifest": False,
            "files": []
        }

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    recognized_count = 0
    file_statuses = []

    for pdf_path in all_pdfs:
        rel_path = str(pdf_path.relative_to(base))
        entry = manifest.get(rel_path)
        if entry:
            is_rec = entry.get("is_recognized", False)
            if is_rec:
                recognized_count += 1
            file_statuses.append({
                "path": rel_path,
                "is_recognized": is_rec,
                "new_name": entry.get("new_name"),
                "used_template": entry.get("used_template")
            })
        else:
            file_statuses.append({
                "path": rel_path,
                "is_recognized": False,
                "new_name": None,
                "used_template": None
            })

    remaining = total - recognized_count
    percent = (recognized_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "recognized": recognized_count,
        "remaining": remaining,
        "percent": round(percent, 2),
        "has_manifest": True,
        "files": file_statuses
    }