class ScannerError(Exception):
    """Базовое исключение сканирования."""

class ScannerNotFoundError(ScannerError):
    """Устройство не найдено."""

class ScannerNotOpenError(ScannerError):
    """Сканер не открыт."""

class ScanCancelledError(ScannerError):
    """Пользователь отменил сканирование в UI драйвера."""