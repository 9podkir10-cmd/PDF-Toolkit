import re
from pathlib import Path
from typing import List, Optional
from backend.manifest import get_manifest_service
from backend.services.template_service import FilenameTemplateService


class PDFFileWorkflow:
    def __init__(self, template_service: FilenameTemplateService):
        self.template_service = template_service

    def apply_rename(self, pdf_path: Path, zone_texts: List[str],
        template_pattern: Optional[str], manual_name: str) -> Path:
        
        if template_pattern is not None:
            placeholders = re.findall(r'\{zone(\d+)\}', template_pattern)
            
            if placeholders:
                if not zone_texts:
                    raise ValueError("Нет распознанных зон для подстановки в шаблон.")
            new_name = self.template_service.render(template_pattern, zone_texts)
            
        else:
            new_name = manual_name.strip() or pdf_path.stem

        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        new_file = pdf_path.parent / new_name

        if new_file != pdf_path:
            pdf_path.rename(new_file)

        return new_file

    def update_manifest_by_record_id(self, record_id: str, manifest_path: Path, template_pattern: Optional[str],
        zone_texts: List[str], structure_pattern: Optional[str] = None, new_path: Optional[Path] = None,) -> None:
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
