from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from PIL import Image

from backend.services.box_to_img import PDFExtractor, Region
from backend.services.ocr_b import OCRBackend
from backend.services.storage import Storage


@dataclass
class OCRZoneResult:
    """Результат OCR для одной зоны."""
    text: str
    storage_id: Optional[str] = None


class OCRWorkflow:
    def __init__(
        self,
        extractor: PDFExtractor,
        ocr: OCRBackend,
        storage: Optional[Storage] = None,
    ):
        self.extractor = extractor
        self.ocr = ocr
        self.storage = storage

    def recognize_zones(
        self,
        pdf_path: str,
        regions: List[Region],
        dpi: int = 300,
    ) -> List[OCRZoneResult]:
        """
        Выполняет OCR для каждой переданной зоны.

        Аргументы:
            pdf_path: путь к PDF-файлу
            regions: список объектов Region (координаты в PDF-пространстве,
                     page – 1-based)
            dpi: разрешение для вырезания изображений

        Возвращает:
            Список OCRZoneResult, где для каждой зоны указан распознанный текст
            и (опционально) идентификатор сохранённого изображения.
        """
        results = []
        for region in regions:
            # 1. Вырезаем изображение
            image = self.extractor.crop_region(pdf_path, region, dpi=dpi)
            if image is None or image.size[0] == 0 or image.size[1] == 0:
                # Можно либо вернуть пустой текст, либо пробросить исключение
                results.append(OCRZoneResult(text=""))
                continue

            # 2. Распознаём
            text = self.ocr.recognize(image)
            clean_text = text.strip()

            # 3. Сохраняем в Storage (если он включён)
            storage_id = None
            if self.storage is not None:
                storage_id = self.storage.save_image(
                    image=image,
                    pdf_path=pdf_path,
                    page=region.page,          # 1-based
                    coords={
                        "x": region.x,
                        "y": region.y,
                        "w": region.w,
                        "h": region.h,
                    },
                    ocr_text=clean_text,
                )

            results.append(OCRZoneResult(text=clean_text, storage_id=storage_id))

        return results

    def update_zone_text(self, storage_id: str, new_text: str) -> None:
        if self.storage is not None:
            self.storage.update_text(storage_id, new_text, is_correction=True)
            
    def ensure_storage(self, enabled: bool, storage_path: Path = Path("ocr_storage")):
        if enabled and self.storage is None:
            self.storage = Storage(storage_path)
        elif not enabled:
            self.storage = None