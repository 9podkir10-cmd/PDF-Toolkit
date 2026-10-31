import json
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image

from backend.indexing.models import Region


class Storage:
    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.images_dir = root_dir / "images"
        self.metadata_file = root_dir / "metadata.json"
        self._metadata: list = self._load_metadata()

    def _load_metadata(self) -> list:
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_metadata(self):
        self.metadata_file.write_text(
            json.dumps(self._metadata, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )

    def save_image(self, image: Image.Image, pdf_path: str, page: int, coords: dict[str, float], ocr_text: str) -> str:
        image_id = uuid.uuid4().hex[:8]
        self.images_dir.mkdir(parents=True, exist_ok=True)
        image.save(self.images_dir / f"{image_id}.png", "PNG")

        self._metadata.append({
            "id": image_id,
            "image": f"{image_id}.png",
            "pdf_path": str(pdf_path),
            "page": page,
            "coords": coords,
            "ocr": ocr_text,
            "corrected": None,
            "created_at": datetime.now().isoformat()
        })
        self._save_metadata()
        return image_id

    def update_text(self, image_id: str, new_text: str, is_correction: bool = True):
        for entry in self._metadata:
            if entry["id"] == image_id:
                entry["corrected" if is_correction else "ocr"] = new_text
                self._save_metadata()
                return
        raise ValueError(f"Image ID {image_id} not found")

    def get_text(self, image_id: str) -> str:
        for entry in self._metadata:
            if entry["id"] == image_id:
                return entry.get("corrected") or entry.get("ocr", "")
        return ""


class OcrToStorage:
    def __init__(self, storage_root: Path = Path("data")):
        self.storage = Storage(storage_root)

    def save_zones_batch(self, pdf_path: str, images: list[Image.Image], regions: list[Region], texts: list[str]) -> list[str | None]:
        storage_ids = []
        for img, region, text in zip(images, regions, texts):
            if not img or img.size[0] == 0 or img.size[1] == 0:
                storage_ids.append(None)
                continue

            sid = self.storage.save_image(
                image=img,
                pdf_path=pdf_path,
                page=region.page,
                coords={"x": region.x, "y": region.y, "w": region.w, "h": region.h},
                ocr_text=text,
            )
            storage_ids.append(sid)
        return storage_ids

    def update_zone_text(self, storage_id: str, new_text: str) -> None:
        if storage_id:
            self.storage.update_text(storage_id, new_text, is_correction=True)

    def get_text(self, storage_id: str) -> str:
        return self.storage.get_text(storage_id)