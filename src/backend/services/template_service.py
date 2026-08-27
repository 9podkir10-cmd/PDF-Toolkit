# backend/services/template_service.py
from typing import List


class FilenameTemplateService:
    @staticmethod
    def render(template: str, zone_texts: List[str]) -> str:
        """
        Подставляет zone_texts в шаблон, заменяя {zone0}, {zone1}, ...
        """
        for i, text in enumerate(zone_texts):
            template = template.replace(f"{{zone{i}}}", text)
        return template