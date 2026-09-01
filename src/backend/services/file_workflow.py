import re
from pathlib import Path
from typing import List, Optional

from backend.manifest import find_manifest
from backend.manifest_center import ManifestCenter
from backend.services.template_service import FilenameTemplateService


class PDFFileWorkflow:
    """
    Сервис, отвечающий за переименование PDF-файлов.
    """
    def __init__(self, template_service: FilenameTemplateService):
        self.template_service = template_service

    def apply_rename(
        self,
        pdf_path: Path,
        zone_texts: List[str],
        template_pattern: Optional[str],
        manual_name: str,
    ) -> Path:
        """
        Формирует новое имя файла, выполняет переименование
        и возвращает новый путь.
        """
        if template_pattern is not None:
            placeholders = re.findall(
                r'\{zone(\d+)\}',
                template_pattern,
            )

            if placeholders:
                if not zone_texts:
                    raise ValueError(
                        "Нет распознанных зон для подстановки "
                        "в шаблон."
                    )

                unique_placeholders = set(placeholders)

                if len(unique_placeholders) != len(zone_texts):
                    raise ValueError(
                        f"Шаблон требует "
                        f"{len(unique_placeholders)} зон, "
                        f"но распознано {len(zone_texts)}."
                    )

            new_name = self.template_service.render(
                template_pattern,
                zone_texts,
            )

        else:
            new_name = manual_name.strip() or pdf_path.stem

        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        new_file = pdf_path.parent / new_name

        if new_file != pdf_path:
            pdf_path.rename(new_file)

        return new_file

    def update_manifest(
        self,
        old_path: Path,
        new_path: Path,
        template_pattern: Optional[str],
        zone_texts: List[str],
        structure_pattern: Optional[str] = None,
    ) -> None:
        manifest_path = find_manifest(old_path)

        if not manifest_path:
            return

        center = ManifestCenter(manifest_path)

        center.update_file_processing(
            old_path=old_path,
            new_path=new_path,
            is_recognized=bool(zone_texts),
            used_template=template_pattern,
            used_structure=structure_pattern,
            zone_texts=zone_texts,
        )