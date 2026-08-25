import os
import pytesseract
from PIL import Image, ImageEnhance
from typing import List, Optional
from pathlib import Path
from backend.config import load_config  

def get_pdf_path(input_path: str) -> Optional[str]:
    path = Path(input_path)
    if path.is_file() and path.suffix.lower() == '.pdf':
        return str(path)
    elif path.is_dir():
        for p in path.rglob('*.pdf'):
            return str(p)
    return None

class OCRBackend:
    def __init__(self, tesseract_path: str, language: str = "eng"):
        self.tesseract_cmd = tesseract_path
        self.reload_from_config()   
        self.language = language

        if not os.path.exists(self.tesseract_cmd):
            raise FileNotFoundError(f"Tesseract не найден по пути: {self.tesseract_cmd}")

        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def reload_from_config(self):
        cfg = load_config()
        tesseract_path = cfg.get("ocr_path", "")
        language = cfg.get("language", "eng")

        if not tesseract_path or not os.path.exists(tesseract_path):
            raise FileNotFoundError(
                f"Tesseract не найден по пути: {tesseract_path}\n"
                "Укажите корректный путь в настройках."
            )

        self.tesseract_cmd = tesseract_path
        self.language = language

    @staticmethod
    def _preprocess(image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        return enhancer.enhance(1.5)

    def recognize(self, image: Image.Image) -> str:
        processed = self._preprocess(image)
        text = pytesseract.image_to_string(processed, lang=self.language)
        return text.strip()

    def recognize_batch(self, images: List[Image.Image]) -> List[str]:
        return [self.recognize(img) for img in images]