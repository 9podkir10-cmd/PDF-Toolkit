from .exceptions import (
    ScanCancelledError,
    ScannerError,
    ScannerNotFoundError,
    ScannerNotOpenError,
)
from .models import ScannedPage, ScannerInfo, ScanRequest, ScanResult
from .service import ScanService

__all__ = [
    "ScanCancelledError",
    "ScanRequest",
    "ScanResult",
    "ScanService",
    "ScannedPage",
    "ScannerError",
    "ScannerInfo",
    "ScannerNotFoundError",
    "ScannerNotOpenError",
]


def get_scan_service() -> ScanService:
    return ScanService()