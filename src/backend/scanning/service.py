import shutil
from pathlib import Path

from PIL import Image

from .drivers.base import BaseScanner
from .drivers.folder import FolderScanner
from .drivers.twain import TwainScanner
from .exceptions import ScannerNotFoundError
from .models import ScannerInfo, ScanRequest


class ScanService:
    def __init__(self, scanner: BaseScanner | None = None):
        self._scanner = scanner
        self._temp_dirs: list[Path] = []

    @staticmethod
    def list_available_devices() -> list[ScannerInfo]:
        try:
            return TwainScanner().list_devices()
        except ScannerNotFoundError:
            return []

    @staticmethod
    def list_folder_devices() -> list[ScannerInfo]:
        return []

    def open_twain(self, device_name: str | None = None) -> None:
        self._scanner = TwainScanner()
        self._scanner.open(device_name)

    def open_folder(self, folder: Path) -> None:
        self._scanner = FolderScanner(folder)
        self._scanner.open()

    def close(self) -> None:
        if self._scanner:
            self._scanner.close()
        for d in self._temp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        self._temp_dirs.clear()

    @property
    def is_open(self) -> bool:
        return self._scanner is not None and self._scanner.is_open

    @property
    def device_name(self) -> str | None:
        return getattr(self._scanner, "_device_name", None)

    def scan(self, request: ScanRequest) -> list[Path]:
        if not self._scanner or not self._scanner.is_open:
            raise RuntimeError("Сканер не открыт.")

        pages = list(
            self._scanner.acquire(
                show_ui=request.show_driver_ui,
                request=request,
            )
        )
        if not pages:
            return []

        images = [p.image for p in pages]

        output_dir = Path(request.output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        scan_dir = output_dir / f"scan_{request.base_filename}"
        scan_dir.mkdir(parents=True, exist_ok=True)

        if request.split_by_count and request.split_by_count > 0:
            return self._save_chunks(images, scan_dir, request)

        return self._save_single(images, scan_dir, request)

    def _save_single(self, images: list[Image.Image], output_dir: Path, request: ScanRequest) -> list[Path]:
        result: list[Path] = []
        for idx, img in enumerate(images, start=1):
            target = output_dir / f"{idx:04d}.bmp"
            img.save(target, format="BMP")
            result.append(target)
        return result

    def _save_chunks(self, images: list[Image.Image], output_dir: Path, request: ScanRequest) -> list[Path]:
        chunk_size = request.split_by_count
        chunks = [
            images[i:i + chunk_size]
            for i in range(0, len(images), chunk_size)
        ]
        result: list[Path] = []
        for idx, chunk in enumerate(chunks, start=1):
            part_dir = output_dir / f"part{idx:02d}"
            part_dir.mkdir(parents=True, exist_ok=True)
            for j, img in enumerate(chunk, start=1):
                target = part_dir / f"{j:04d}.bmp"
                img.save(target, format="BMP")
                result.append(target)
        return result