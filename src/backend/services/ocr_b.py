import os, pytesseract
from PIL import Image, ImageEnhance
from typing import List
from backend.config import get_config_service

class OCRBackend:
    def __init__(self, tesseract_path: str = None, language: str = None):
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
        text = pytesseract.image_to_string(processed, lang=self.language)
        return text.strip()

    def recognize_batch(self, images: List[Image.Image]) -> List[str]:
        self._ensure_tesseract()
        return [self.recognize(img) for img in images]