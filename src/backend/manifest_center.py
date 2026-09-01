from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class ManifestCenter:
    def __init__(self, path: Path):
        self.path = Path(path)

    @classmethod
    def for_folder(cls, folder: Path) -> "ManifestCenter":
        return cls(Path(folder) / "manifest.json")

    # ------------------------------------------------------------------
    # Low-level persistence
    # ------------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_record(
        self,
        manifest: Dict[str, Any],
        record_key: str,
    ) -> tuple[str, Dict[str, Any]] | None:
        """
        Пока record_key фактически является filename/key.
        На следующем этапе это можно заменить на настоящий immutable ID.
        """
        for section in ("unique", "duplicates"):
            records = manifest.get(section, {})

            if record_key in records:
                return section, records[record_key]

        return None

    def _find_record_by_path(
        self,
        manifest: Dict[str, Any],
        path: Path,
    ) -> tuple[str, str, Dict[str, Any]] | None:
        """
        Ищет запись по original_path.
        Возвращает:
            section, record_key, entry
        """
        target = str(path)

        for section in ("unique", "duplicates"):
            records = manifest.get(section, {})

            if not isinstance(records, dict):
                continue

            for record_key, entry in records.items():
                if not isinstance(entry, dict):
                    continue

                if entry.get("original_path") == target:
                    return section, record_key, entry

        return None

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def update_ocr(
        self,
        record_key: str,
        *,
        is_recognized: bool,
        used_template: Optional[str],
        used_structure: Optional[str],
        zone_texts: List[str],
    ) -> bool:
        manifest = self.load()

        found = self._find_record(manifest, record_key)

        if found is None:
            return False

        _, record = found

        record["ocr"] = {
            "is_recognized": is_recognized,
            "used_template": used_template,
            "used_structure": used_structure,
            "zone_texts": list(zone_texts),
        }

        self.save(manifest)
        return True

    def update_ocr_by_path(
        self,
        path: Path,
        *,
        is_recognized: bool,
        used_template: Optional[str],
        used_structure: Optional[str],
        zone_texts: List[str],
    ) -> bool:
        manifest = self.load()

        found = self._find_record_by_path(manifest, path)

        if found is None:
            return False

        _, _, record = found

        record["ocr"] = {
            "is_recognized": is_recognized,
            "used_template": used_template,
            "used_structure": used_structure,
            "zone_texts": list(zone_texts),
        }

        self.save(manifest)
        return True

    def rename_record(
        self,
        record_key: str,
        *,
        new_filename: str,
        new_path: Path,
    ) -> bool:
        manifest = self.load()

        found = self._find_record(manifest, record_key)

        if found is None:
            return False

        section, record = found

        records = manifest[section]

        if record_key != new_filename:
            if new_filename in records:
                raise ValueError(
                    f"Manifest record already exists: {new_filename}"
                )

            del records[record_key]
            records[new_filename] = record

        record["original_path"] = new_path.as_posix()

        # Пока схема использует filename как ID.
        # Поэтому обновляем все ссылки на старое имя.
        if section == "unique":
            for duplicate in manifest.get("duplicates", {}).values():
                if not isinstance(duplicate, dict):
                    continue

                if duplicate.get("links_to") == record_key:
                    duplicate["links_to"] = new_filename

        self.save(manifest)
        return True

    def rename_record_by_path(
        self,
        old_path: Path,
        *,
        new_filename: str,
        new_path: Path,
    ) -> bool:
        manifest = self.load()

        found = self._find_record_by_path(manifest, old_path)

        if found is None:
            return False

        section, record_key, record = found

        records = manifest[section]

        if record_key != new_filename:
            if new_filename in records:
                raise ValueError(
                    f"Manifest record already exists: {new_filename}"
                )

            del records[record_key]
            records[new_filename] = record

        record["original_path"] = new_path.as_posix()

        if section == "unique":
            for duplicate in manifest.get("duplicates", {}).values():
                if not isinstance(duplicate, dict):
                    continue

                if duplicate.get("links_to") == record_key:
                    duplicate["links_to"] = new_filename

        self.save(manifest)
        return True

    def mark_structured(
        self,
        record_key: str,
        *,
        moved_to: str,
    ) -> bool:
        manifest = self.load()

        found = self._find_record(manifest, record_key)

        if found is None:
            return False

        _, record = found

        record["structured"] = True
        record["moved_to"] = moved_to

        self.save(manifest)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_ocr_recognized(
        self,
        record_key: str,
    ) -> bool:
        manifest = self.load()

        found = self._find_record(manifest, record_key)

        if found is None:
            return False

        _, record = found

        ocr = record.get("ocr")

        if not isinstance(ocr, dict):
            return False

        return bool(ocr.get("is_recognized", False))

    def get_pending_files(self) -> List[Path]:
        manifest = self.load()

        skip_original_paths: set[str] = set()

        duplicates = manifest.get("duplicates", {})

        if isinstance(duplicates, dict):
            for entry in duplicates.values():
                if not isinstance(entry, dict):
                    continue

                original_path = entry.get("original_path")

                if original_path:
                    skip_original_paths.add(
                        str(Path(original_path).resolve())
                    )

        unique = manifest.get("unique", {})

        if isinstance(unique, dict):
            for entry in unique.values():
                if not isinstance(entry, dict):
                    continue

                ocr = entry.get("ocr")

                if (
                    isinstance(ocr, dict)
                    and ocr.get("is_recognized", False)
                ):
                    original_path = entry.get("original_path")

                    if original_path:
                        skip_original_paths.add(
                            str(Path(original_path).resolve())
                        )

        all_pdfs = list(self.path.parent.rglob("*.pdf"))

        pending: List[Path] = []

        for pdf_path in all_pdfs:
            resolved = pdf_path.resolve()

            if str(resolved) in skip_original_paths:
                continue

            pending.append(resolved)

        return pending
    
    
    def update_file_processing(
    self,
    old_path: Path,
    new_path: Path,
    *,
    is_recognized: bool,
    used_template: Optional[str],
    used_structure: Optional[str],
    zone_texts: List[str],
) -> bool:
        manifest = self.load()

        found = self._find_record_by_path(
            manifest,
            old_path,
        )

        if found is None:
            # fallback для текущей схемы
            found_by_name = self._find_record(
                manifest,
                old_path.name,
            )

            if found_by_name is None:
                return False

            section, record = found_by_name
            record_key = old_path.name

        else:
            section, record_key, record = found

        record["ocr"] = {
            "is_recognized": is_recognized,
            "used_template": used_template,
            "used_structure": used_structure,
            "zone_texts": list(zone_texts),
        }

        new_filename = new_path.name

        if record_key != new_filename:
            records = manifest[section]

            if new_filename in records:
                raise ValueError(
                    f"Manifest record already exists: {new_filename}"
                )

            del records[record_key]
            records[new_filename] = record

            if section == "unique":
                for duplicate in manifest.get(
                    "duplicates",
                    {},
                ).values():
                    if not isinstance(duplicate, dict):
                        continue

                    if duplicate.get("links_to") == record_key:
                        duplicate["links_to"] = new_filename

        record["original_path"] = new_path.as_posix()

        self.save(manifest)

        return True