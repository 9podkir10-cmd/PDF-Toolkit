from abc import ABC, abstractmethod
from typing import Iterator, List

from .models import ScannerInfo, ScannedPage


class Scanner(ABC):

    @abstractmethod
    def list_devices(self) -> List[ScannerInfo]:
        """Return available scanners."""
        raise NotImplementedError

    @abstractmethod
    def open(self, device_name: str) -> None:
        """Open scanner by name."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close scanner and release resources."""
        raise NotImplementedError

    @abstractmethod
    def acquire(self) -> Iterator[ScannedPage]:
        """Acquire pages from scanner."""
        raise NotImplementedError

    @abstractmethod
    def cancel(self) -> None:
        """Cancel active acquisition."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def device_name(self) -> str | None:
        raise NotImplementedError
