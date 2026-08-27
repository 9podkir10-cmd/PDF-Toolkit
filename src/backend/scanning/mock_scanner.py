"""
Мок-сканер для тестирования без физического устройства.
Генерирует тестовые изображения или читает их из папки.
"""
from typing import Iterator, List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import os
import random

from .models import ScannerInfo, ScannedPage
from .scanner import Scanner


class MockScanner(Scanner):
    """Имитирует сканер, создавая тестовые страницы."""

    def __init__(self, num_pages: int = 5, image_folder: Optional[str] = None):
        """
        :param num_pages: количество генерируемых страниц (если нет папки)
        :param image_folder: путь к папке с готовыми изображениями (PNG/JPG)
        """
        self._is_open = False
        self._device_name = "Mock Scanner"
        self._num_pages = num_pages
        self._image_folder = image_folder
        self._page_counter = 0

    def list_devices(self) -> List[ScannerInfo]:
        return [ScannerInfo(name="Mock Scanner", manufacturer="Test")]

    def open(self, device_name: str) -> None:
        self._is_open = True
        self._device_name = device_name

    def close(self) -> None:
        self._is_open = False

    def configure(self, settings: Dict[str, Any]) -> None:
        # Имитация применения настроек (ничего не делаем)
        pass

    def acquire(self) -> Iterator[ScannedPage]:
        if not self._is_open:
            raise RuntimeError("Сканер не открыт.")

        if self._image_folder and os.path.isdir(self._image_folder):
            # Читаем изображения из папки
            image_files = [f for f in os.listdir(self._image_folder)
                           if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            if not image_files:
                raise RuntimeError("В папке нет изображений.")
            for idx, img_file in enumerate(image_files, start=1):
                img_path = os.path.join(self._image_folder, img_file)
                pil_img = Image.open(img_path)
                yield ScannedPage(image=pil_img, page_number=idx)
        else:
            # Генерируем тестовые страницы
            for i in range(1, self._num_pages + 1):
                # Создаём изображение с номером страницы и случайным "шумом"
                img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                # Рисуем рамку
                draw.rectangle([10, 10, 790, 990], outline=(0, 0, 0), width=2)
                # Текст с номером страницы
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
                draw.text((350, 450), f"Page {i}", fill=(0, 0, 0), font=font)
                # Добавляем небольшой "штрих-код" на некоторых страницах для теста патчей
                if i % 2 == 0:
                    # Имитация patch-кода (просто черный прямоугольник)
                    draw.rectangle([300, 700, 500, 750], fill=(0, 0, 0))
                yield ScannedPage(image=img, page_number=i)

    def cancel(self) -> None:
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "dpi": [200, 300],
            "color_modes": ["color", "gray"],
            "duplex": [True, False],
            "page_sizes": ["A4"],
        }

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name