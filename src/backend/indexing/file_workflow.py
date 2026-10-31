import re
import time
from pathlib import Path

from backend.manifest import get_manifest_service


class PDFFileWorkflow:
    def __init__(self):
        pass

    def _render_template(self, template: str, zone_texts: list[str]) -> str:
        for i, text in enumerate(zone_texts):
            template = template.replace(f"{{zone{i}}}", text)
        return template

    def _safe_rename(self, old_path: Path, new_path: Path, retries: int = 5, delay: float = 0.5) -> None:
        for attempt in range(retries):
            try:
                old_path.rename(new_path)
                return
            except PermissionError as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)

    def apply_rename(
        self, 
        pdf_path: Path, 
        zone_texts: list[str],
        template_pattern: str | None, 
        manual_name: str
    ) -> Path:

        # 1. Генерация имени
        if template_pattern is not None:
            placeholders = re.findall(r'\{zone(\d+)\}', template_pattern)
            if placeholders and not zone_texts:
                raise ValueError("Нет распознанных зон для подстановки в шаблон.")
            
            new_name = self._render_template(template_pattern, zone_texts)
        else:
            new_name = manual_name.strip() or pdf_path.stem

        # 2. Добавление расширения
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        new_file = pdf_path.parent / new_name

        # 3. Переименование (с защитой от блокировки ОС)
        if new_file != pdf_path:
            self._safe_rename(pdf_path, new_file)

        return new_file

    def update_manifest_by_record_id(
        self, 
        record_id: str, 
        manifest_path: Path, 
        template_pattern: str | None,
        zone_texts: list[str], 
        structure_pattern: str | None = None, 
        new_path: Path | None = None
    ) -> None:
        service = get_manifest_service(str(manifest_path))
        manifest = service.load()
        if manifest is None:
            print(f"⚠️ Манифест не загружен: {manifest_path}")
            return

        record = service.get_record(record_id)
        if record is None:
            print(f"⚠️ Запись с ID {record_id} не найдена")
            return

        # Обновляем OCR
        record.ocr.status = "completed" if zone_texts else "failed"
        record.ocr.is_recognized = bool(zone_texts)
        record.ocr.used_template = template_pattern
        record.structure.used_structure = structure_pattern
        record.ocr.zone_texts = zone_texts
        
        if new_path is not None:
            record.filename = new_path.name

        service.save()