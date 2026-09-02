from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, ValidationInfo

# для вложенных структур
class DeduplicationInfo(BaseModel):
    stage: int = Field(default=0, ge=0, le=4, description="Этап обработки дедупликации (0-4)")
    is_duplicate: bool = Field(default=False, description="Является ли файл дубликатом")
    links_to: Optional[str] = Field(default=None, description="ID оригинального файла, если это дубликат")
    linked_files: List[str] = Field(default_factory=list, description="ID файлов-дубликатов, если это оригинал")

class OcrInfo(BaseModel):
    status: str = Field(default="pending", description="Статус OCR: pending, processing, completed, failed, not_processed")
    is_recognized: bool = Field(default=False, description="Был ли текст успешно распознан")
    used_template: Optional[str] = Field(default=None, description="Имя использованного OCR-шаблона")
    zone_texts: List[str] = Field(default_factory=list, description="Список распознанных текстов из зон")

class StructureInfo(BaseModel):
    structured: bool = Field(default=False, description="Был ли файл структурирован")
    used_structure: Optional[str] = Field(default=None, description="Использованная структура для именования")
    moved_to: Optional[str] = Field(default=None, description="Относительный путь, куда был перемещён файл")

# запись об одном файле
class FileRecord(BaseModel):
    filename: str = Field(..., description="Имя файла")
    original_path: str = Field(..., description="Полный путь к исходному файлу")
    size: int = Field(..., gt=0, escription="Размер файла в байтах")
    hash: Optional[str] = Field(default=None, description="Хеш-сумма файла SHA-256")


    deduplication: DeduplicationInfo = Field(default_factory=DeduplicationInfo)
    ocr: OcrInfo = Field(default_factory=OcrInfo)
    structure: StructureInfo = Field(default_factory=StructureInfo)


# верний уровень
class SourceConfig(BaseModel):
    directory: str = Field(..., description="Путь к исходной папке с документами")

class OutputConfig(BaseModel):
     directory: str = Field(..., description="Путь к папке для структурированных файлов (hardlink)")

class PipelineStatus(BaseModel):
    status: str = Field(default="idle", description="Статус пайплайна: idle, running, completed, failed")

class Statistics(BaseModel):
    total: int = Field(default=0, ge=0, description="Общее количество файлов")
    processed: int = Field(default=0, ge=0, description="Количество обработанных файлов")
    unique: int = Field(default=0, ge=0, description="Количество уникальных файлов")
    duplicates: int = Field(default=0, ge=0, description="Количество файлов-дубликатов")
    errors: int = Field(default=0, ge=0, description="Количество файлов с ошибками")
    total_size_bytes: int = Field(default=0, ge=0, description="Общий размер всех файлов в байтах")

# информация о манифесте
class Manifest(BaseModel):
    schema_version: int = Field(default=2, ge=1, description="Версия схемы манифеста")
    manifest_id: str = Field(default_factory=lambda: uuid4().hex, description="Уникальный идентификатор манифеста")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата и время создания манифеста")
    updated_at: datetime = Field(default_factory=datetime.now, description="Дата и время последнего обновления")
    source: SourceConfig = Field(..., description="Конфигурация источника")
    output: OutputConfig = Field(..., description="Конфигурация вывода")
    pipeline: PipelineStatus = Field(default_factory=PipelineStatus, description="Статус выполнения пайплайна")
    stats: Statistics = Field(default_factory=Statistics, description="Статистика обработки")

    records: Dict[str, FileRecord] = Field(default_factory=dict, description="Словарь записей о файлах (ключ — ID файла)")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Список ошибок, возникших при обработке")

    # валидаторы
    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, value: datetime, info: ValidationInfo) -> datetime:
        created_at = info.data.get("created_at")
        if created_at and value < created_at:
            raise ValueError("updated_at не может быть раньше created_at")
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "schema_version": 2,
                    "manifest_id": "a1b2c3d4e5f67890a1b2c3d4e5f67890",
                    "created_at": "2026-09-02T10:15:30.123456+00:00",
                    "updated_at": "2026-09-02T10:45:12.654321+00:00",
                    "source": {"directory": "/mnt/storage/documents"},
                    "output": {"directory": "/mnt/storage/documents_hardlink"},
                    "pipeline": {"status": "completed"},
                    "stats": {
                        "total": 3,
                        "processed": 3,
                        "unique": 2,
                        "duplicates": 1,
                        "errors": 0,
                        "total_size_bytes": 593920,
                    },
                    "records": {
                        "6f3a9c0d7b4e4b4a9d1c2f8e6a5b3c21": {
                            "filename": "invoice_2026_001.pdf",
                            "original_path": "/mnt/storage/documents/invoice_2026_001.pdf",
                            "size": 245760,
                            "hash": "a4c5d6e7f8a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef",
                            "deduplication": {
                                "stage": 4,
                                "is_duplicate": False,
                                "links_to": None,
                                "linked_files": None,
                            },
                            "ocr": {
                                "status": "completed",
                                "is_recognized": True,
                                "used_template": "invoice_template",
                                "zone_texts": ["ООО Ромашка", "ИНН 1234567890", "Сумма: 10 000 руб."],
                            },
                            "structure": {
                                "structured": True,
                                "used_structure": "year/company",
                                "moved_to": "2026/Ромашка/invoice_2026_001_ООО Ромашка.pdf",
                            },
                        },
                    },
                    "errors": [],
                }
            ]
        },
        # названия полей, а не алиасы, при генерации JSON Schema
        "use_enum_values": True,
        # Сортировать поля для стабильности JSON Schema
        "json_schema_serialization_defaults_required": True,
    }