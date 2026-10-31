
from pydantic import BaseModel, Field


class Region(BaseModel):
    page: int = Field(..., ge=1, description="Номер страницы (начиная с 1)")
    x: float = Field(..., description="Координата X (в точках PDF)")
    y: float = Field(..., description="Координата Y (в точках PDF)")
    w: float = Field(..., gt=0, description="Ширина области")
    h: float = Field(..., gt=0, description="Высота области")


class RecognizedZone(BaseModel): # Выделенная область + Распознанный текст + ID в хранилище
    region: Region = Field(..., description="Координаты рамки на странице")
    text: str = Field(default="", description="Распознанный текст")
    storage_id: str | None = Field(default=None, description="ID записи в хранилище")


class OCRSession(BaseModel):
    
    # --- Информация о файлах ---
    input_mode: str = Field(default="file", description="Режим работы: 'file' или 'folder'")
    pdf_path: str | None = Field(default=None, description="Путь к текущему открытому PDF")
    manifest_path: str | None = Field(default=None, description="Путь к файлу manifest.json")
    record_id: str | None = Field(default=None, description="ID текущего файла в манифесте")
    
    # --- Очередь файлов (если открыта папка) ---
    queue_ids: list[str] = Field(default_factory=list, description="Список ID файлов для обработки")
    current_index: int = Field(default=-1, description="Индекс текущего файла в очереди")
    
    # --- Состояние выделения ---
    locked: bool = Field(default=False, description="Включен ли режим блокировки (Lock)")
    locked_zones: list[Region] = Field(default_factory=list, description="Шаблоны зон, сохраненные при блокировке")
    
    # --- Результаты работы ---
    zones: list[RecognizedZone] = Field(default_factory=list, description="Список всех выделенных и распознанных зон")