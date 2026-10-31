import os
from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageEnhance

from backend.config import get_config_service
from backend.constants import OCR_DPI
from backend.indexing.models import RecognizedZone, Region
from backend.indexing.storage import OcrToStorage


class BoxToImg:
    def crop_regions(self, pdf_path: str, regions: list[Region], dpi: int = OCR_DPI) -> list[Image.Image]:
        if not regions:
            return []

        images = []
        pdf_bytes = Path(pdf_path).read_bytes()
        
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            for region in regions:
                page = doc[region.page - 1]
                rect = pymupdf.Rect(region.x, region.y, region.x + region.w, region.y + region.h)
                pix = page.get_pixmap(clip=rect, dpi=dpi)
                img = Image.open(BytesIO(pix.tobytes("png")))
                images.append(img)
            return images

    def crop_region(self, pdf_path: str, region: Region, dpi: int = OCR_DPI) -> Image.Image:
        images = self.crop_regions(pdf_path, [region], dpi)
        return images[0] if images else None


class ImgToText:
    def __init__(self, tesseract_path: str | None = None, language: str | None = None):
        self.config_service = get_config_service()
        config = self.config_service.get_config()
        
        self.tesseract_cmd = tesseract_path or config.ocr_path
        self.language = language or config.language
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _ensure_tesseract(self):
        if not self.tesseract_cmd or not os.path.exists(self.tesseract_cmd):
            self.reload_from_config()
            
        if not self.tesseract_cmd or not os.path.exists(self.tesseract_cmd):
            raise FileNotFoundError(
                f"Tesseract не найден по пути: {self.tesseract_cmd}\n"
                "Укажите корректный путь в настройках."
            )
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def reload_from_config(self):
        config = self.config_service.get_config()
        self.tesseract_cmd = config.ocr_path
        self.language = config.language
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    @staticmethod
    def _preprocess(image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        return enhancer.enhance(1.5)

    def recognize(self, image: Image.Image) -> str:
        self._ensure_tesseract()
        processed = self._preprocess(image)
        
        try:
            text = pytesseract.image_to_string(processed, lang=self.language, config="--oem 3")
            return text.strip()
        except Exception as e:
            raise RuntimeError(
                f"OCR ERROR\n"
                f"Tesseract: {self.tesseract_cmd}\n"
                f"Language: {self.language}\n"
                f"Exists: {os.path.exists(self.tesseract_cmd)}\n"
                f"Error: {e}"
            ) from e

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        self._ensure_tesseract()
        return [self.recognize(img) for img in images]


class OCREngine:
    def __init__(self, storage_service: OcrToStorage | None = None):
        self.extractor = BoxToImg()
        self.recognizer = ImgToText()
        self.storage = storage_service

    def enable_storage(self, enabled: bool, storage_path: Path = Path("data")):
        if enabled:
            if not self.storage:
                self.storage = OcrToStorage(storage_path)
        else:
            self.storage = None

    def process_regions(self, pdf_path: str, regions: list[Region]) -> list[RecognizedZone]:
        if not regions:
            return []

        # 1. Вырезаем картинки
        images = self.extractor.crop_regions(pdf_path, regions)

        # 2. Распознаем текст
        texts = self.recognizer.recognize_batch(images)

        # 3. Формируем зоны
        zones: list[RecognizedZone] = []
        for region, text in zip(regions, texts):
            zones.append(RecognizedZone(region=region, text=text))

        # 4. Сохраняем через storage service (если он есть)
        if self.storage:
            storage_ids = self.storage.save_zones_batch(
                pdf_path=pdf_path,
                images=images,
                regions=regions,
                texts=texts,
            )
            for zone, sid in zip(zones, storage_ids):
                zone.storage_id = sid

        return zones

    def update_zone_text(self, storage_id: str, new_text: str) -> None:
        if self.storage:
            self.storage.update_zone_text(storage_id, new_text)
