# backend/services/queue_service.py
from pathlib import Path
import json
from typing import List

from backend.manifest import load_manifest, is_ocr_recognized


class PDFQueueService:
    @staticmethod
    def get_pending(folder: Path) -> List[Path]:
        """
        Возвращает список PDF в папке, которые ещё не распознаны.
        Учитывает:
          - unique с is_recognized=True
          - duplicates, где original_path уже обработан
        """
        base = Path(folder)
        manifest_path = base / "manifest.json"
        skip_original_paths = set()

        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            duplicates = manifest.get('duplicates', {})
            if isinstance(duplicates, dict):
                for entry in duplicates.values():
                    if isinstance(entry, dict):
                        orig = entry.get('original_path')
                        if orig:
                            skip_original_paths.add(str(Path(orig).resolve()))

            unique = manifest.get('unique', {})
            if isinstance(unique, dict):
                for entry in unique.values():
                    if not isinstance(entry, dict):
                        continue
                    ocr = entry.get('ocr')
                    if isinstance(ocr, dict) and ocr.get('is_recognized', False):
                        orig = entry.get('original_path')
                        if orig:
                            skip_original_paths.add(str(Path(orig).resolve()))

        all_pdfs = list(base.rglob("*.pdf"))
        pending = []

        for p in all_pdfs:
            p_resolved = p.resolve()
            should_skip = False

            for skip_orig_str in skip_original_paths:
                try:
                    skip_path = Path(skip_orig_str).resolve()
                    if p_resolved.samefile(skip_path):
                        should_skip = True
                        break
                except (FileNotFoundError, OSError):
                    if str(p_resolved) == skip_orig_str:
                        should_skip = True
                        break

            if not should_skip:
                pending.append(p_resolved)

        return pending