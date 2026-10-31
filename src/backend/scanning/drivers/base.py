# src/backend/scanning/drivers/base.py
from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..models import ScannedPage, ScannerInfo


class BaseScanner(ABC):
    """Абстрактный интерфейс сканера."""

    @abstractmethod
    def list_devices(self) -> list[ScannerInfo]:
        """Возвращает список доступных устройств."""
        ...

    @abstractmethod
    def open(self, device_name: str | None = None) -> None:
        """Открывает устройство."""
        ...

    @abstractmethod
    def acquire(self, show_ui: bool = True) -> Iterator[ScannedPage]:
        """Запускает сканирование. Yields страницы по мере поступления."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Закрывает устройство."""
        ...

    @property
    @abstractmethod
    def is_open(self) -> bool:
        ...