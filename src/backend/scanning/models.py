from dataclasses import dataclass, field
from typing import List, Optional
from PIL import Image

@dataclass(frozen=True)
class ScannerInfo:
    name: str
    manufacturer: Optional[str] = None
    product_family: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ScannedPage:
    image: object
    page_number: int
    
@dataclass
class Page:
    """Представляет одну страницу."""
    image: Image.Image
    page_number: int
    # Можно добавить путь к файлу, если изображение загружено с диска
    file_path: Optional[str] = None

@dataclass
class Document:
    """Представляет один документ, состоящий из страниц."""
    pages: List[Page] = field(default_factory=list)

@dataclass
class Batch:
    """Представляет пачку (Batch), содержащую один или несколько документов."""
    name: str
    documents: List[Document] = field(default_factory=list)