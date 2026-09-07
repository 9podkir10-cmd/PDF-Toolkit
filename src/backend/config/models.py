from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Template(BaseModel):
    name: str = Field(..., description="Название шаблона (отображается в интерфейсе)")
    pattern: str = Field(..., description="Шаблон переименования файла (используйте {zone0}, {zone1}, ...)")
    structure: Optional[str] = Field(None, description="Шаблон структуры папок (оставьте пустым, если не требуется)")

class ScanProfile(BaseModel):
    name: str = Field(..., description="Название профиля: Light / Dark / High Quality")
    dpi: int = Field(300, ge=50, le=1200, description="Разрешение сканирования в точках на дюйм")
    color_mode: str = Field("color", description="Цветовой режим: color / gray / bw")
    page_size: str = Field("A4", description="Размер страницы: A4, A5, Letter, Legal")
    file_format: str = Field("pdf", description="Формат выходного файла: pdf / jpeg / png")
    brightness: int = Field(0, ge=-100, le=100, description="Яркость (от -100 до 100)")
    contrast: int = Field(0, ge=-100, le=100, description="Контрастность (от -100 до 100)")
    duplex: bool = Field(False, description="Двустороннее сканирование")

class Config(BaseModel):
    ocr_path: str = Field("", description="Путь к исполняемому файлу Tesseract OCR")
    language: str = Field("rus+eng", description="Язык распознавания: rus+eng / rus / eng")
    ocr_storage_enabled: bool = Field(False, description="Сохранять ли результаты OCR в локальное хранилище")
    templates: List[Template] = Field(default_factory=list, description="Список шаблонов переименования и структуризации")
    selected_template_index: int = Field(-1, ge=-1, description="Индекс выбранного шаблона (-1 — не выбран)")
    scan_profiles: List[ScanProfile] = Field(default_factory=list, description="Список профилей сканирования")

    # валидаторы
    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        import re
        if not re.match(r'^[a-zA-Z+]+$', value):
            raise ValueError("Язык должен содержать только латинские буквы, '+'")
        return value

    @field_validator("selected_template_index")
    @classmethod
    def validate_selected_index(cls, value: int, info) -> int:
        templates = info.data.get("templates")
        if templates is not None and value != -1:
            if value < -1 or value >= len(templates):
                raise ValueError(
                    f"selected_template_index ({value}) вне допустимого диапазона "
                    f"для {len(templates)} шаблонов."
                )
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ocr_path": "C:/Users/User/OneDrive/Desktop/pod/PDF Toolkit/Tesseract-OCR/tesseract.exe",
                    "language": "eng",
                    "ocr_storage_enabled": False,
                    "templates": [
                        {
                            "name": "договор",
                            "pattern": "Договор на имя {zone0} №{zone1}",
                            "structure": "Договоры/{zone0}"
                        },
                        {
                            "name": "Счет {zone0} Номер-{zone1}",
                            "pattern": "Счет {zone0} Номер-{zone1}",
                            "structure": "Счета/№{zone1}"
                        }
                    ],
                    "selected_template_index": 1,
                    "scan_profiles": [
                        {
                            "name": "Light",
                            "dpi": 300,
                            "color_mode": "color",
                            "page_size": "A4",
                            "file_format": "pdf",
                            "brightness": 3,
                            "contrast": 1
                        }
                    ]
                }
            ]
        },
        "use_enum_values": True,
        "json_schema_serialization_defaults_required": True,
    }