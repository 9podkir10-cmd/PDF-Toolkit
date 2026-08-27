from typing import Iterator, List, Optional, Dict, Any
from PIL import Image

from .models import ScannerInfo, ScannedPage
from .mock_scanner import Scanner

try:
    import twain
except ImportError:
    twain = None


class TwainScanner(Scanner):
    """Реализация сканера через TWAIN (pytwain)."""

    def __init__(self):
        self._source_manager = None
        self._device = None
        self._device_name: Optional[str] = None

    # ----- Вспомогательные методы -----

    def _require_twain(self):
        """Проверяет, доступна ли библиотека TWAIN."""
        if twain is None:
            raise RuntimeError(
                "TWAIN support is unavailable. "
                "Install the pytwain package."
            )

    def _twain_to_pil(self, twain_image) -> Image.Image:
        """
        Преобразует изображение TWAIN в PIL Image.
        Скопировано из оригинального scan_b.py.
        """
        # Определяем режим по битности
        if hasattr(twain_image, 'bits_per_pixel') and twain_image.bits_per_pixel == 1:
            mode = '1'
        elif hasattr(twain_image, 'bits_per_pixel') and twain_image.bits_per_pixel == 8:
            mode = 'L'
        else:
            mode = 'RGB'

        # Извлекаем данные
        data = getattr(twain_image, 'data', None)
        if data is None:
            raise ValueError("Нет данных изображения")
        if not isinstance(data, bytes):
            data = bytes(data)

        return Image.frombytes(mode, (twain_image.columns, twain_image.rows), data)

    # ----- Реализация интерфейса Scanner -----

    def list_devices(self) -> List[ScannerInfo]:
        """Возвращает список доступных сканеров."""
        self._require_twain()

        sm = twain.SourceManager()
        try:
            result = []
            # В некоторых версиях pytwain используется source_list
            sources = getattr(sm, 'source_list', [])
            if not sources:
                # Альтернативный способ: открыть источник с пустым именем?
                # Просто пробуем получить список через стандартный метод
                sources = sm.sources if hasattr(sm, 'sources') else []
            for src_name in sources:
                result.append(ScannerInfo(name=src_name))
            return result
        finally:
            sm.close()

    def open(self, device_name: str) -> None:
        """Открывает сканер по имени."""
        self._require_twain()

        # Закрываем предыдущее соединение
        self.close()

        try:
            self._source_manager = twain.SourceManager()
            self._device = self._source_manager.open_source(device_name)

            if self._device is None:
                self._source_manager.close()
                self._source_manager = None
                raise RuntimeError(f"Не удалось открыть сканер: {device_name}")

            self._device_name = device_name

        except Exception as exc:
            self.close()
            raise RuntimeError(f"Ошибка открытия сканера '{device_name}': {exc}") from exc

    def close(self) -> None:
        """Закрывает сканер и освобождает ресурсы."""
        device = self._device
        source_manager = self._source_manager

        self._device = None
        self._source_manager = None
        self._device_name = None

        if device is not None:
            try:
                device.close()
            except Exception:
                pass

        if source_manager is not None:
            try:
                source_manager.close()
            except Exception:
                pass

    def configure(self, settings: Dict[str, Any]) -> None:
        """
        Применяет настройки сканирования к открытому устройству.
        Параметры:
            dpi (int): разрешение
            color_mode (str): 'color', 'gray', 'bw'
            duplex (bool): дуплексный режим
        """
        if self._device is None:
            raise RuntimeError("Сканер не открыт.")

        caps = self._device.capabilities

        # Установка цветового режима
        color_mode = settings.get("color_mode", "color")
        if color_mode == "color":
            caps.ICAP_PIXELTYPE.set(twain.PixelType.RGB)
        elif color_mode == "gray":
            caps.ICAP_PIXELTYPE.set(twain.PixelType.GRAY)
        else:  # 'bw'
            caps.ICAP_PIXELTYPE.set(twain.PixelType.BW)

        # Установка разрешения
        dpi = settings.get("dpi", 300)
        caps.ICAP_XRESOLUTION.set(dpi)
        caps.ICAP_YRESOLUTION.set(dpi)

        # Установка дуплекса
        duplex = settings.get("duplex", False)
        caps.ICAP_DUPLEX.set(duplex)

    def acquire(self) -> Iterator[ScannedPage]:
        """
        Захватывает страницы со сканера.
        Возвращает итератор по ScannedPage.
        """
        if self._device is None:
            raise RuntimeError("Сканер не открыт.")

        try:
            self._device.request_acquire()
            page_number = 0

            while True:
                # Внимание: в разных версиях pytwain метод может называться
                # xfer_image_native или xfer_image_natively.
                # Проверьте документацию вашей версии.
                # По умолчанию используем xfer_image_native (без 'ly').
                rv = self._device.xfer_image_native()

                if rv is None:
                    break

                # Если вернулся список, обрабатываем каждый элемент
                if isinstance(rv, (list, tuple)):
                    images = rv
                else:
                    images = [rv]

                for img in images:
                    page_number += 1
                    pil_image = self._twain_to_pil(img)
                    yield ScannedPage(image=pil_image, page_number=page_number)

        except Exception as exc:
            raise RuntimeError(f"Ошибка сканирования: {exc}") from exc

    def cancel(self) -> None:
        """Отменяет текущий процесс сканирования (если поддерживается)."""
        if self._device is None:
            return
        try:
            # В некоторых версиях pytwain есть метод cancel
            if hasattr(self._device, 'cancel'):
                self._device.cancel()
        except Exception:
            pass

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Возвращает поддерживаемые возможности сканера.
        Пока заглушка, в будущем можно реализовать реальный опрос.
        """
        # Заглушка для совместимости
        return {
            "dpi": [150, 200, 300, 400, 600],
            "color_modes": ["bw", "gray", "color"],
            "duplex": [True, False],
            "page_sizes": ["A4", "Letter"],
        }

    @property
    def is_open(self) -> bool:
        return self._device is not None

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name