from pathlib import Path
from typing import List, Dict, Any
from backend.config import get_config_service
from backend.services.box_to_img import PDFExtractor, Region
from backend.services.ocr_b import OCRBackend
from backend.services.storage import Storage


class OCRService:
    def __init__(self, storage_root: Path = Path("data")):
        self.extractor = PDFExtractor()

        config_service = get_config_service()
        config = config_service.get_config()
        tesseract_path = config.ocr_path
        language = config.language

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

        images = self.extractor.crop_regions(
            pdf_path=file_path,
            regions=pdf_regions,
            dpi=300
        )

        texts = self.ocr.recognize_batch(images)

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