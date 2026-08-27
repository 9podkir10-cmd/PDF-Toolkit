import re
from pathlib import Path
from typing import List, Optional
import json
from backend.manifest import find_manifest, update_manifest_for_file
from backend.services.template_service import FilenameTemplateService


class PDFFileWorkflow:
    """
    Сервис, отвечающий за переименование PDF-файлов и обновление manifest.json
    после успешного распознавания.
    """

    def __init__(self, template_service: FilenameTemplateService):
        self.template_service = template_service

    def apply_rename(self, pdf_path: Path, zone_texts: List[str], template_pattern: Optional[str], manual_name: str) -> Path:
        """
        Формирует новое имя файла на основе шаблона или ручного ввода,
        выполняет переименование и возвращает новый путь.

        :param pdf_path: путь к исходному файлу
        :param zone_texts: список распознанных текстов зон
        :param template_pattern: шаблон из настроек (может быть None)
        :param manual_name: имя, введённое пользователем вручную
        :return: новый путь к файлу (или старый, если имя не изменилось)
        :raises ValueError: если шаблон требует больше зон, чем есть, или зоны отсутствуют
        """
        # 1. Определяем новое имя
        if template_pattern is not None:
            placeholders = re.findall(r'\{zone(\d+)\}', template_pattern)
            if placeholders:
                if not zone_texts:
                    raise ValueError("Нет распознанных зон для подстановки в шаблон.")
                unique_placeholders = set(placeholders)
                if len(unique_placeholders) != len(zone_texts):
                    raise ValueError(
                        f"Шаблон требует {len(unique_placeholders)} зон, но распознано {len(zone_texts)}."
                    )
            new_name = self.template_service.render(template_pattern, zone_texts)
        else:
            new_name = manual_name.strip() or pdf_path.stem

        # 2. Добавляем расширение .pdf, если его нет
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        # 3. Переименовываем, если имя изменилось
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
        structure_pattern: Optional[str] = None,   # новое
    ) -> None:
        """
        Обновляет manifest.json:
        - находит запись по старому пути (original_path)
        - обновляет ocr-информацию (шаблон переименования, структуру, тексты зон)
        - если имя изменилось, переименовывает ключ и обновляет original_path
        """
        manifest_path = find_manifest(old_path)  # или new_path – они в одной папке
        if not manifest_path:
            return

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception:
            return

        old_path_str = str(old_path)
        new_name = new_path.name

        # Ищем запись по original_path (старый путь)
        found_entry = None
        found_section = None
        found_key = None

        for section in ('unique', 'duplicates'):
            for key, entry in manifest.get(section, {}).items():
                if entry.get('original_path') == old_path_str:
                    found_entry = entry
                    found_section = section
                    found_key = key
                    break
            if found_entry:
                break

        # Если не нашли по original_path, пробуем по старому имени (для обратной совместимости)
        if not found_entry:
            old_name = old_path.name
            for section in ('unique', 'duplicates'):
                if old_name in manifest.get(section, {}):
                    found_entry = manifest[section][old_name]
                    found_section = section
                    found_key = old_name
                    break

        if not found_entry:
            return

        # Обновляем ocr-информацию
        ocr_info = {
            "is_recognized": bool(zone_texts),
            "used_template": template_pattern,
            "used_structure": structure_pattern,   # новое
            "zone_texts": zone_texts.copy(),       # сохраняем копию списка
        }
        found_entry['ocr'] = ocr_info

        # Если имя изменилось, переименовываем ключ и обновляем original_path
        if found_key != new_name and found_section is not None:
            del manifest[found_section][found_key]
            manifest[found_section][new_name] = found_entry
            found_entry['original_path'] = str(new_path)

        # Сохраняем манифест
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)