from pathlib import Path
from typing import Iterator, Optional, List
from PIL import Image
from .base import BaseScanner
from ..models import ScannerInfo, ScannedPage
from ..exceptions import ScannerNotOpenError

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

class FolderScanner(BaseScanner):
    def __init__(self, folder: Path):
        self._folder = Path(folder)
        self._opened = False

    def list_devices(self) -> List[ScannerInfo]:
        return [ScannerInfo(name=str(self._folder), driver="folder")]

    def open(self, device_name: Optional[str] = None) -> None:
        self._opened = True

    def acquire(self, show_ui: bool = True) -> Iterator[ScannedPage]:
        if not self._opened:
            raise ScannerNotOpenError("Folder-сканер не открыт.")

        files = sorted(
            p for p in self._folder.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTS
        )
        for i, path in enumerate(files, start=1):
            yield ScannedPage(page_number=i, image=Image.open(path))

    def close(self) -> None:
        self._opened = False

    @property
    def is_open(self) -> bool:
        return self._opened