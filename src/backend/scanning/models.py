from pathlib import Path
from typing import Optional, List
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict
from dataclasses import dataclass, field
from typing import List
from PIL import Image


@dataclass
class Page:
    page_number: int
    image: Image.Image


@dataclass
class Document:
    name: str = ""
    pages: List[Page] = field(default_factory=list)


@dataclass
class Batch:
    name: str = ""
    documents: List[Document] = field(default_factory=list)

class ScannerInfo(BaseModel):
    name: str = Field(..., description="Имя устройства в системе")
    driver: str = Field(..., description="Тип драйвера: twain, folder, ...")
    is_default: bool = False
    is_open: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ScannedPage(BaseModel):
    page_number: int = Field(..., ge=1)
    image: Image.Image = Field(..., description="PIL-изображение")
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ScanResult(BaseModel):
    pages: List[ScannedPage] = Field(default_factory=list)
    scanner_name: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
class ScanRequest(BaseModel):
    output_folder: Path = Field(..., description="Куда сохранять результаты")
    base_filename: str = Field("scan", description="Базовое имя файла")
    file_format: str = Field("bmp", description="pdf / jpeg / png / bmp")
    split_by_barcode: bool = False
    barcode_modes: List[str] = Field(default_factory=lambda: ["patch1", "patch2", "patch3", "patch4", "patchT"])
    split_by_count: Optional[int] = Field(None, ge=1)
    show_driver_ui: bool = Field(True, description="Показывать ли UI драйвера (Avision)")

    dpi: Optional[int] = None
    color_mode: Optional[str] = None        # "color" / "gray" / "bw"
    page_size: Optional[str] = None         # "A4", "A5", "Letter", "Legal"
    brightness: Optional[int] = None
    contrast: Optional[int] = None
    duplex: Optional[bool] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)