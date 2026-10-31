from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field


@dataclass
class Page:
    page_number: int
    image: Image.Image


@dataclass
class Document:
    name: str = ""
    pages: list[Page] = field(default_factory=list)


@dataclass
class Batch:
    name: str = ""
    documents: list[Document] = field(default_factory=list)

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
    pages: list[ScannedPage] = Field(default_factory=list)
    scanner_name: str | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
class ScanRequest(BaseModel):
    output_folder: Path = Field(..., description="Куда сохранять результаты")
    base_filename: str = Field("scan", description="Базовое имя файла")
    file_format: str = Field("bmp", description="pdf / jpeg / png / bmp")
    split_by_barcode: bool = False
    barcode_modes: list[str] = Field(default_factory=lambda: ["patch1", "patch2", "patch3", "patch4", "patchT"])
    split_by_count: int | None = Field(None, ge=1)
    show_driver_ui: bool = Field(True, description="Показывать ли UI драйвера (Avision)")

    scan_dpi: int | None = None
    color_mode: str | None = None        # "color" / "gray" / "bw"
    page_size: str | None = None         # "A4", "A5", "Letter", "Legal"
    brightness: int | None = None
    contrast: int | None = None
    duplex: bool | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)