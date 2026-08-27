"""
FolderScanner - реализация сканера, читающего изображения из папки.
Используется для тестирования без физического устройства.
"""

import os
from typing import Iterator, List, Optional, Dict, Any
from PIL import Image
from pathlib import Path

from .models import ScannerInfo, ScannedPage
from .scanner import Scanner


class FolderScanner(Scanner):
    """Сканер, который вместо TWAIN читает изображения из указанной папки."""

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self._image_files: List[str] = []
        self._is_open = False
        self._device_name = f"Папка: {os.path.basename(folder_path)}"

    # ---------- Реализация абстрактных методов ----------

    def list_devices(self) -> List[ScannerInfo]:
        """Возвращает информацию о данном 'сканере'."""
        return [ScannerInfo(name=self._device_name, manufacturer="Folder")]

    def open(self, device_name: str) -> None:
        """Открывает папку и сканирует список изображений."""
        if not os.path.isdir(self.folder_path):
            raise FileNotFoundError(f"Папка не найдена: {self.folder_path}")

        # Собираем все поддерживаемые файлы изображений в папке (без рекурсии)
        self._image_files = [
            str(p) for p in Path(self.folder_path).glob("*")
            if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        ]

        if not self._image_files:
            raise RuntimeError(f"В папке '{self.folder_path}' нет изображений.")

        self._is_open = True

    def close(self) -> None:
        """Закрывает сканер (освобождает ресурсы)."""
        self._is_open = False

    def configure(self, settings: Dict[str, Any]) -> None:
        """Настройки для FolderScanner игнорируются."""
        pass

    def acquire(self) -> Iterator[ScannedPage]:
        """Генерирует страницы из загруженных изображений."""
        if not self._is_open:
            raise RuntimeError("Сканер не открыт.")

        for idx, file_path in enumerate(self._image_files, start=1):
            try:
                img = Image.open(file_path)
                # Приводим к RGB для единообразия
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                yield ScannedPage(image=img, page_number=idx)
            except Exception as e:
                # Логируем ошибку, но продолжаем с остальными файлами
                print(f"Ошибка загрузки {file_path}: {e}")

    def cancel(self) -> None:
        """Отмена сканирования (для FolderScanner ничего не делает)."""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Возвращает возможности (заглушка)."""
        return {
            "dpi": [],
            "color_modes": [],
            "duplex": [],
            "page_sizes": [],
        }

    # ---------- Свойства (обязательные для интерфейса) ----------

    @property
    def is_open(self) -> bool:
        """Возвращает, открыт ли сканер."""
        return self._is_open

    @property
    def device_name(self) -> Optional[str]:
        """Возвращает имя устройства."""
        return self._device_name