from .service import ScanService
from .models import ScanRequest, ScanResult, ScannedPage, ScannerInfo
from .exceptions import (
    ScannerError,
    ScannerNotFoundError,
    ScannerNotOpenError,
    ScanCancelledError,
)

__all__ = [
    "ScanService",
    "ScanRequest",
    "ScanResult",
    "ScannedPage",
    "ScannerInfo",
    "ScannerError",
    "ScannerNotFoundError",
    "ScannerNotOpenError",
    "ScanCancelledError",
]


def get_scan_service() -> ScanService:
    return ScanService()