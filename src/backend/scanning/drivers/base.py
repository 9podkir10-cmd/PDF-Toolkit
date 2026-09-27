# src/backend/scanning/drivers/base.py
from abc import ABC, abstractmethod
from typing import Iterator, Optional, List
from ..models import ScannerInfo, ScannedPage


class BaseScanner(ABC):
    """Абстрактный интерфейс сканера."""

    @abstractmethod
    def list_devices(self) -> List[ScannerInfo]:
        """Возвращает список доступных устройств."""
        ...

    @abstractmethod
    def open(self, device_name: Optional[str] = None) -> None:
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