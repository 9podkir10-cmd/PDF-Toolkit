# extract_pages.py
import fitz
from PIL import Image
from io import BytesIO
from dataclasses import dataclass
from typing import List, Union

@dataclass
class Region:
    page: int
    x: float
    y: float
    w: float
    h: float

class PDFExtractor:
    def crop_region(
        self,
        pdf_path: str,
        region: Region,
        dpi: int = 300
    ) -> Image.Image:
        doc = fitz.open(pdf_path)
        try:
            page = doc[region.page - 2]  # fitz нумерует с 0
            rect = fitz.Rect(
                region.x,
                region.y,
                region.x + region.w,
                region.y + region.h
            )
            pix = page.get_pixmap(clip=rect, dpi=dpi)
            img = Image.open(BytesIO(pix.tobytes("png")))
            return img
        finally:
            doc.close()

    def crop_regions(
        self,
        pdf_path: str,
        regions: List[Region],
        dpi: int = 300
    ) -> List[Image.Image]:
        images = []
        for region in regions:
            images.append(self.crop_region(pdf_path, region, dpi))
        return images