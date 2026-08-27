import os
import pytesseract
from PIL import Image, ImageEnhance
from typing import List, Optional
from pathlib import Path
from backend.config import load_config  

class OCRBackend:
    def __init__(self, tesseract_path: str, language: str = "eng"):
        self.tesseract_cmd = tesseract_path
        self.language = language

    def _ensure_tesseract(self):
        if not self.tesseract_cmd:
            self.reload_from_config()
        if not self.tesseract_cmd or not os.path.exists(self.tesseract_cmd):
            raise FileNotFoundError(
                f"Tesseract не найден по пути: {self.tesseract_cmd}\n"
                "Укажите корректный путь в настройках."
            )
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def reload_from_config(self):
        cfg = load_config()
        tesseract_path = cfg.get("ocr_path", "")
        language = cfg.get("language", "eng")
        self.tesseract_cmd = tesseract_path
        self.language = language

    @staticmethod
    def _preprocess(image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        return enhancer.enhance(1.5)

    def recognize(self, image: Image.Image) -> str:
        self._ensure_tesseract()  # проверка перед вызовом
        processed = self._preprocess(image)
        text = pytesseract.image_to_string(processed, lang=self.language)
        return text.strip()

    def recognize_batch(self, images: List[Image.Image]) -> List[str]:
        self._ensure_tesseract()  # проверка перед вызовом
        return [self.recognize(img) for img in images]
