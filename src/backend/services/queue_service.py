from pathlib import Path
from typing import List
from backend.manifest import get_manifest_service

class PDFQueueService:
    @staticmethod
    def get_pending(folder: Path) -> List[str]:
        """
        Возвращает список record_id файлов, которые ещё не распознаны.
        Учитывает:
          - уникальные файлы (is_duplicate=False) с is_recognized=False
          - дубликаты пропускаются (is_duplicate=True)
        """
        base = Path(folder)
        manifest_path = base / "manifest.json"
        service = get_manifest_service(str(manifest_path))
        manifest = service.load()
        if manifest is None:
            return []

        pending_ids = []
        for record_id, record in manifest.records.items():
            if record.deduplication.is_duplicate:
                continue
            if not record.ocr.is_recognized:
                file_path = base / record.filename
                if file_path.exists():
                    pending_ids.append(record_id)
        return pending_ids