# ocr_service.py
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
from backend.config import load_config
from services.box_to_img import PDFExtractor, Region
from services.ocr_b import OCRBackend
from storage import Storage


class OCRService:
    def __init__(self, tesseract_path: str, storage_root: Path = Path("data")):
        self.extractor = PDFExtractor()
        config = load_config()
        tesseract_path = config.get("ocr_path", "")
        language = config.get("language", "rus+eng")
        self.ocr = OCRBackend(tesseract_path=tesseract_path, language=language)

        self.storage = Storage(storage_root)

    def recognize(self, file_path: str, regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pdf_regions = []
        for r in regions:
            pdf_regions.append(
                Region(
                    page=r['page'],
                    x=r['rect_pdf'].x0,
                    y=r['rect_pdf'].y0,
                    w=r['rect_pdf'].width,
                    h=r['rect_pdf'].height
                )
            )

        images: List[Image.Image] = self.extractor.crop_regions(
            pdf_path=file_path,
            regions=pdf_regions,
            dpi=300
        )

        texts: List[str] = self.ocr.recognize_batch(images)

        results = []
        for img, text, pdf_reg, src_reg in zip(images, texts, pdf_regions, regions):
            image_id = self.storage.save_image(
                image=img,
                pdf_path=file_path,
                page=pdf_reg.page,
                coords={
                    "x": src_reg["x"],
                    "y": src_reg["y"],
                    "w": src_reg["w"],
                    "h": src_reg["h"],
                },
                ocr_text=text
            )

            results.append({
                "page": pdf_reg.page,
                "coords": {
                    "x": src_reg["x"],
                    "y": src_reg["y"],
                    "w": src_reg["w"],
                    "h": src_reg["h"],
                },
                "text": text,
                "image_path": str(self.storage.images_dir / f"{image_id}.png")
            })

        return results