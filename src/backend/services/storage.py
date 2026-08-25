# storage.py
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from datetime import datetime

class Storage:
    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.images_dir = root_dir / "images"
        self.metadata_file = root_dir / "metadata.json"

        self._metadata: list = self._load_metadata()

    def _load_metadata(self) -> list:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_metadata(self):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    def save_image(
        self,
        image: Image.Image,
        pdf_path: str,
        page: int,
        coords: Dict[str, float],
        ocr_text: str
    ) -> str:

        image_id = uuid.uuid4().hex[:8]
        image_path = self.images_dir / f"{image_id}.png"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        image.save(image_path, "PNG")

        entry = {
            "id": image_id,
            "image": f"{image_id}.png",
            "pdf_path": str(pdf_path),
            "page": page,
            "coords": coords,
            "ocr": ocr_text,
            "corrected": None,
            "created_at": datetime.now().isoformat()
        }

        self._metadata.append(entry)
        self._save_metadata()

        return image_id

    def update_text(self, image_id: str, new_text: str, is_correction: bool = True):
        for entry in self._metadata:
            if entry["id"] == image_id:
                if is_correction:
                    entry["corrected"] = new_text
                else:
                    entry["ocr"] = new_text
                self._save_metadata()
                return
        raise ValueError(f"Image ID {image_id} not found")

    def get_metadata(self, image_id: str) -> Optional[Dict[str, Any]]:
        for entry in self._metadata:
            if entry["id"] == image_id:
                return entry
        return None

    def get_all_metadata(self) -> list:
        return self._metadata

    def get_text(self, image_id: str) -> str:
        entry = self.get_metadata(image_id)
        if not entry:
            return ""
        return entry.get("corrected") or entry.get("ocr", "")