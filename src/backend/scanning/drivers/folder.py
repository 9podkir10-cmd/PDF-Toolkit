from collections.abc import Iterator
from pathlib import Path

from PIL import Image

from ..exceptions import ScannerNotOpenError
from ..models import ScannedPage, ScannerInfo
from .base import BaseScanner

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

class FolderScanner(BaseScanner):
    def __init__(self, folder: Path):
        self._folder = Path(folder)
        self._opened = False

    def list_devices(self) -> list[ScannerInfo]:
        return [ScannerInfo(name=str(self._folder), driver="folder")]

    def open(self, device_name: str | None = None) -> None:
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