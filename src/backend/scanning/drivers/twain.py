from io import BytesIO
from typing import Iterator, Optional, List
from PIL import Image
from .base import BaseScanner
from ..models import ScannerInfo, ScannedPage, ScanRequest
from ..exceptions import ScannerNotFoundError, ScannerNotOpenError

try:
    import twain
    from twain.lowlevel import constants as twain_const
except ImportError:
    twain = None
    twain_const = None


class TwainScanner(BaseScanner):
    def __init__(self):
        if twain is None:
            raise ScannerNotFoundError("Библиотека pytwain не установлена.")
        self._source_manager = None
        self._source = None
        self._device_name: Optional[str] = None

    def list_devices(self) -> List[ScannerInfo]:
        devices: List[ScannerInfo] = []
        sm = twain.SourceManager()
        try:
            for name in sm.source_list:
                devices.append(ScannerInfo(name=name, driver="twain"))
        finally:
            sm.close()
        return devices

    def open(self, device_name: Optional[str] = None) -> None:
        self._source_manager = twain.SourceManager()
        if device_name:
            self._source = self._source_manager.open_source(device_name)
        else:
            self._source = self._source_manager.open_source()
        if not self._source:
            raise ScannerNotFoundError("Не удалось открыть TWAIN-источник.")
        self._device_name = self._source.name

    def apply_request(self, request: ScanRequest) -> None:
        """Применяет параметры профиля к TWAIN-источнику."""
        if not self._source:
            return

        def _set(cap, typ, value):
            try:
                self._source.set_capability(cap, typ, value)
            except Exception as e:
                print(f"[TwainScanner] Не удалось установить {cap}: {e}")

        # Разрешение
        if request.dpi:
            _set(twain.ICAP_XRESOLUTION, twain.TWTY_FIX32, float(request.dpi))
            _set(twain.ICAP_YRESOLUTION, twain.TWTY_FIX32, float(request.dpi))

        # Цветовой режим
        if request.color_mode:
            pixel_map = {
                "color": twain.TWPT_RGB,
                "gray": twain.TWPT_GRAY,
                "bw": twain.TWPT_BW,
            }
            pt = pixel_map.get(request.color_mode)
            if pt is not None:
                _set(twain.ICAP_PIXELTYPE, twain.TWTY_UINT16, pt)

        # Двустороннее сканирование
        if request.duplex is not None:
            _set(twain.CAP_DUPLEXENABLED, twain.TWTY_BOOL, request.duplex)

        # Яркость / контраст
        if request.brightness is not None:
            brightness_value = float(request.brightness) * 10.0
            _set(twain.ICAP_BRIGHTNESS, twain.TWTY_FIX32, brightness_value)

        if request.contrast is not None:
            contrast_value = float(request.contrast) * 10.0
            _set(twain.ICAP_CONTRAST, twain.TWTY_FIX32, contrast_value)

        # Размер страницы
        if request.page_size:
            size_map = {
                "A4": twain_const.TWSS_A4LETTER,
                "A5": twain_const.TWSS_A5,
                "LETTER": twain_const.TWSS_USLETTER,
                "LEGAL": twain_const.TWSS_USLEGAL,
            }
            size = size_map.get(request.page_size.upper())
            if size is not None:
                _set(twain_const.ICAP_SUPPORTEDSIZES, twain_const.TWTY_UINT16, size)

    def acquire(self, show_ui: bool = True, request: Optional[ScanRequest] = None) -> Iterator[ScannedPage]:
        if not self._source:
            raise ScannerNotOpenError("Сканер не открыт.")

        if request is not None:
            self.apply_request(request)

        self._source.request_acquire(show_ui=show_ui, modal_ui=True)

        page_num = 1
        while True:
            try:
                handle, remaining = self._source.xfer_image_natively()
            except twain.exceptions.TwainError:
                break
            if handle == 0:
                break

            bmp_bytes = twain.dib_to_bm_file(handle)
            image = Image.open(BytesIO(bmp_bytes))
            yield ScannedPage(page_number=page_num, image=image)
            page_num += 1

            if remaining <= 0:
                break

    def close(self) -> None:
        if self._source:
            try:
                self._source.close()
            except Exception:
                pass
            self._source = None
        if self._source_manager:
            try:
                self._source_manager.close()
            except Exception:
                pass
            self._source_manager = None

    @property
    def is_open(self) -> bool:
        return self._source is not None