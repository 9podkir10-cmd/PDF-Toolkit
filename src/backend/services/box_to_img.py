import pymupdf
from PIL import Image
from io import BytesIO
from dataclasses import dataclass
from typing import List
from backend.constants import OCR_DPI


@dataclass
class Region:
    page: int
    x: float
    y: float
    w: float
    h: float

class PDFExtractor:
    def crop_regions(self, pdf_path: str, regions: List[Region], dpi: int = OCR_DPI) -> List[Image.Image]:
        if not regions:
            return []

        images = []
        doc = pymupdf.open(pdf_path)
        try:
            for region in regions:
                page = doc[region.page - 1]
                rect = pymupdf.Rect(
                    region.x,
                    region.y,
                    region.x + region.w,
                    region.y + region.h
                )
                pix = page.get_pixmap(clip=rect, dpi=dpi)
                img = Image.open(BytesIO(pix.tobytes("png")))
                images.append(img)
            return images
        finally:
            doc.close()

    def crop_region(self, pdf_path: str, region: Region, dpi: int = OCR_DPI) -> Image.Image:
        images = self.crop_regions(pdf_path, [region], dpi)
        return images[0] if images else None