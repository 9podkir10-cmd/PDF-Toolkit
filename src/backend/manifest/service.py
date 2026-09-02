import datetime
from typing import Optional
from uuid import uuid4
from .models import Manifest, FileRecord, DeduplicationInfo, Statistics, SourceConfig, OutputConfig
from .repository import ManifestRepository

class ManifestService:
    def __init__(self, repo: ManifestRepository):
        self._repo = repo
        self._manifest: Optional[Manifest] = None

    def load_or_create(self, source_dir: str, output_dir: str, total: int = 0) -> Manifest:
        if self._repo.exists():
            self._manifest = self._repo.load()
            return self._manifest
        else:
            return self.create(source_dir, output_dir, total)

    def create(self, source_dir: str, output_dir: str, total: int = 0) -> Manifest:
        self._manifest = Manifest(
            source=SourceConfig(directory=source_dir),
            output=OutputConfig(directory=output_dir),
            stats=Statistics(total=total, processed=0, unique=0, duplicates=0, errors=0),
        )
        self._repo.save(self._manifest)
        return self._manifest

    def save(self) -> None:
        if self._manifest:
            self._repo.save(self._manifest)

    def add_record(self, filename: str, original_path: str, size: int, stage: int, hash_value: Optional[str] = None,
        is_duplicate: bool = False, links_to: Optional[str] = None) -> FileRecord:

        if self._manifest is None:
            raise RuntimeError("Manifest not loaded")
        record_id = uuid4().hex
        record = FileRecord(
            filename=filename,
            original_path=original_path,
            size=size,
            hash=hash_value or "",
            deduplication=DeduplicationInfo(
                stage=stage,
                is_duplicate=is_duplicate,
                links_to=links_to,
            ),
        )
        self._manifest.records[record_id] = record

        self._update_stats()
        return record_id   

    def get_record(self, record_id: str) -> Optional[FileRecord]:
        if self._manifest is None:
            return None
        return self._manifest.records.get(record_id)

    def link_duplicate(self, duplicate_id: str, original_id: str) -> None:
        if self._manifest is None:
            return
        dup = self._manifest.records.get(duplicate_id)
        orig = self._manifest.records.get(original_id)
        if dup and orig:
            dup.deduplication.is_duplicate = True
            dup.deduplication.links_to = original_id
            if original_id not in orig.deduplication.linked_files:
                orig.deduplication.linked_files.append(duplicate_id)
            self._update_stats()

    def add_error(self, path: str, stage: int, error: str) -> None:
        if self._manifest is None:
            return
        self._manifest.errors.append({
            "path": path,
            "stage": stage,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })
        self._manifest.stats.errors += 1

    def get_manifest(self) -> Manifest:
        return self._manifest

    def get_stats(self) -> Statistics:
        return self._manifest.stats if self._manifest else Statistics()

    def _update_stats(self) -> None:
        if self._manifest is None:
            return
        records = self._manifest.records.values()
        total = len(records)
        unique = sum(1 for r in records if not r.deduplication.is_duplicate)
        duplicates = total - unique
        processed = sum(1 for r in records if r.ocr.status not in ("pending", "processing"))
        total_size = sum(r.size for r in records)
        self._manifest.stats.total = total
        self._manifest.stats.unique = unique
        self._manifest.stats.duplicates = duplicates
        self._manifest.stats.processed = processed
        self._manifest.stats.total_size_bytes = total_size
        
    def load(self) -> Optional[Manifest]:
        try:
            self._manifest = self._repo.load()
            return self._manifest
        except FileNotFoundError:
            return None
    
    def exists(self) -> bool:
        return self._repo.exists()