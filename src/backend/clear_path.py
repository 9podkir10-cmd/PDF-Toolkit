from pathlib import Path
from typing import List, Dict
import os
import hashlib
from datetime import datetime
from backend.manifest_center import ManifestCenter
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

class DirectoryNormalizer:
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = self.source_dir.parent / f"{self.source_dir.name}_hardlink"
        self.manifest_center = ManifestCenter.for_folder(self.output_dir)
        self.manifest_path = self.manifest_center.path

        self.pdf_files = self._discover_all_pdfs()
        if not self.pdf_files:
            raise Exception(f"В папке {self.source_dir} нет PDF файлов!")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_workers = min(32, (multiprocessing.cpu_count() or 1) + 4)
    
    def _calculate_file_hash(self, file_path: Path, bytes_count: int = None) -> str:
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                if bytes_count:
                    chunk = f.read(bytes_count)
                    hash_sha256.update(chunk)
                else:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except OSError as exc:
            raise RuntimeError(f"Не удалось прочитать файл для хеширования: {file_path}") from exc

    def _compare_byte_by_byte(self, file1_path: Path, file2_path: Path) -> bool:
        try:
            with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
                while True:
                    chunk1 = f1.read(65536)
                    chunk2 = f2.read(65536)
                    if len(chunk1) != len(chunk2):
                        return False
                    if chunk1 != chunk2:
                        return False
                    if not chunk1:
                        return True
        except Exception:
            return False
    
    def _create_hardlink(self, source_path: Path, target_path: Path) -> Path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        candidate = target_path
        counter = 0
        
        while True:
            try:
                os.link(source_path, candidate)
                return candidate
            except FileExistsError:
                try:
                    if os.path.samefile(source_path, candidate):
                        return candidate
                except OSError:
                    pass
                
                counter += 1
                candidate = (
                    target_path.parent
                    / f"{target_path.stem}_{counter}{target_path.suffix}"
                )

    def _discover_all_pdfs(self) -> List[Dict]:
        pdf_files = []
        for pdf_path in self.source_dir.rglob("*.pdf", case_sensitive=False):
            if pdf_path.is_file():
                try:
                    if self.output_dir in pdf_path.parents:
                        continue
                    file_size = pdf_path.stat().st_size
                    if file_size == 0:
                        continue
                    pdf_files.append({
                        'path': pdf_path,
                        'size': file_size,
                    })
                except Exception:
                    continue
        pdf_files.sort(key=lambda x: x["path"].as_posix().casefold())
        return pdf_files
    
    def _generate_filename(self, file_info: dict, stage: int, hash_value: str = None) -> str:
        stem = file_info['path'].stem
        size = file_info['size']
        if stage == 1:
            return f"{stem}_{size}.pdf"
        elif stage == 2:
            partial_hash = hash_value
            return f"{stem}_{size}_{partial_hash[:8]}.pdf"
        elif stage in (3, 4):
            return f"{hash_value}.pdf"
        else:
            raise ValueError(f"Неизвестный этап: {stage}")
    
    def _add_to_manifest(self, manifest: dict, file_info: dict, new_name: str, 
                        stage: int, hash_value: str = None, is_duplicate: bool = False,
                        links_to: str = None) -> None:
        if is_duplicate:
            manifest['duplicates'][new_name] = {
                'original_path': file_info['path'].as_posix(),
                'hash': hash_value,
                'size': file_info['size'],
                'is_duplicate': True,
                'stage': stage,
                'links_to': links_to
            }
            manifest['stats']['duplicates'] += 1
        else:
            manifest['unique'][new_name] = {
                'original_path': file_info['path'].as_posix(),
                'hash': hash_value,
                'size': file_info['size'],
                'is_duplicate': False,
                'stage': stage
            }
            manifest['stats']['unique'] += 1
    
    def _stage1_group_by_size(self) -> Dict:
        size_groups = defaultdict(list)
        for file_info in self.pdf_files:
            size_groups[str(file_info['size'])].append(file_info)
        return size_groups

    def _stage2_partial_hash(self, size_groups: Dict, manifest: Dict) -> Dict:
        partial_hash_groups = defaultdict(list)
        files_to_hash = []  # список (size_key, file_info) для параллельной обработки
        
        for size_key, files in size_groups.items():
            if len(files) == 1:
                file_info = files[0]
                new_name = self._generate_filename(file_info, stage=1)
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                self._add_to_manifest(manifest, file_info, new_name, stage=1)
            else:
                for file_info in files:
                    files_to_hash.append((size_key, file_info))
        
        if not files_to_hash:
            return partial_hash_groups
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_info = {
                executor.submit(self._calculate_file_hash, info['path'], 4096): (key, info)
                for key, info in files_to_hash
            }
            for future in as_completed(future_to_info):
                size_key, file_info = future_to_info[future]
                try:
                    partial_hash = future.result()
                except Exception as exc:
                    manifest["stats"]["errors"] += 1
                    manifest["errors"].append({
                        "path": str(file_info["path"]),
                        "stage": 2,
                        "error": str(exc),
                    })
                    continue
                group_key = f"{size_key}_{partial_hash}"
                partial_hash_groups[group_key].append(file_info)               
        for group in partial_hash_groups.values():
            group.sort(key=lambda info: info["path"].as_posix().casefold())        
        return partial_hash_groups           

    def _stage3_full_hash(self, partial_hash_groups: Dict, manifest: Dict) -> Dict:
        full_hash_groups = defaultdict(list)
        files_to_hash = []
        
        for key, files in partial_hash_groups.items():
            if len(files) == 1:
                file_info = files[0]
                partial_hash = key.split('_')[1]
                new_name = self._generate_filename(file_info, stage=2, hash_value=partial_hash)
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                self._add_to_manifest(manifest, file_info, new_name, stage=2, hash_value=partial_hash)
            else:
                for file_info in files:
                    files_to_hash.append(file_info)
        
        if not files_to_hash:
            return full_hash_groups
               
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_info = {
                executor.submit(self._calculate_file_hash, info['path']): info
                for info in files_to_hash
            }
            for future in as_completed(future_to_info):
                file_info = future_to_info[future]
                try:
                    full_hash = future.result()
                except Exception as exc:
                    manifest["stats"]["errors"] += 1
                    manifest["errors"].append({
                        "path": str(file_info["path"]),
                        "stage": 3,
                        "error": str(exc),
                    })
                    continue
                full_hash_groups[full_hash].append(file_info)
                
        for group in full_hash_groups.values():
            group.sort(key=lambda info: info["path"].as_posix().casefold())        
        return full_hash_groups
    
    def _stage4_byte_by_byte(self, full_hash_groups: Dict, manifest: Dict) -> None:
        for full_hash, files in full_hash_groups.items():
            if len(files) == 1:
                file_info = files[0]
                new_name = self._generate_filename(file_info, stage=3, hash_value=full_hash)
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                self._add_to_manifest(manifest, file_info, new_name, stage=3, hash_value=full_hash)
            else:
                unique_files, duplicate_pairs = self._separate_unique_and_duplicates(files)
                self._process_unique_files(unique_files, full_hash, manifest)
                self._process_duplicates(duplicate_pairs, unique_files, full_hash, manifest)

    def _separate_unique_and_duplicates(self, files: List[Dict]) -> tuple:
        unique_files = []
        duplicate_pairs = []
        for file_info in files:
            is_duplicate = False
            for unique_file in unique_files:
                if self._compare_byte_by_byte(file_info['path'], unique_file['path']):
                    is_duplicate = True
                    duplicate_pairs.append((file_info, unique_file))
                    break
            if not is_duplicate:
                unique_files.append(file_info)
        return unique_files, duplicate_pairs

    def _process_unique_files(self, unique_files: List[Dict], full_hash: str, manifest: Dict) -> None:
        for file_info in unique_files:
            new_name = self._generate_filename(file_info, stage=4, hash_value=full_hash)
            target_path = self.output_dir / new_name
            counter = 0
            while target_path.exists():
                counter += 1
                new_name = f"{full_hash}_{counter}.pdf"
                target_path = self.output_dir / new_name
            self._create_hardlink(file_info['path'], target_path)
            self._add_to_manifest(manifest, file_info, new_name, stage=4, hash_value=full_hash)
            file_info['unique_name'] = new_name

    def _process_duplicates(self, duplicate_pairs: List[tuple], unique_files: List[Dict], 
                            full_hash: str, manifest: Dict) -> None:
        for file_info, original_file in duplicate_pairs:
            original_name = None
            for uf in unique_files:
                if uf['path'] == original_file['path']:
                    original_name = uf.get('unique_name')
                    break
            if original_name and original_name in manifest['unique']:
                dup_counter = len(manifest['unique'][original_name].get('linked_files', [])) + 1
                dup_name = f"{full_hash}_dup{dup_counter}.pdf"
                self._add_to_manifest(
                    manifest, file_info, dup_name, stage=4,
                    hash_value=full_hash, is_duplicate=True, links_to=original_name
                )
                manifest['unique'][original_name].setdefault('linked_files', []).append(dup_name)

    def normalize_structure(self) -> Dict:
        if self.output_dir.exists() and self.manifest_path.exists():
            manifest = self.manifest_center.load()
            return {
                'unique': manifest.get('unique', {}),
                'duplicates': manifest.get('duplicates', {}),
                'stats': manifest.get('stats', {}),
                'structure': {
                    'source_dir': self.source_dir.as_posix(),
                    'output_dir': self.output_dir.as_posix(),
                    'manifest_path': self.manifest_path.as_posix(),
                    'total_files': manifest.get('stats', {}).get('total', 0),
                    'unique_files': manifest.get('stats', {}).get('unique', 0),
                    'duplicate_files': manifest.get('stats', {}).get('duplicates', 0)
                }
            }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            'source_dir': self.source_dir.as_posix(),
            'output_dir': self.output_dir.as_posix(),
            'created_at': datetime.now().isoformat(),
            'stats': {
                'total': len(self.pdf_files),
                'unique': 0,
                'duplicates': 0,
                'errors': 0
            },
            'duplicates': {},
            'unique': {},
            'errors': []
        }
        
        size_groups = self._stage1_group_by_size()
        partial_hash_groups = self._stage2_partial_hash(size_groups, manifest)
        full_hash_groups = self._stage3_full_hash(partial_hash_groups, manifest)
        self._stage4_byte_by_byte(full_hash_groups, manifest)
        
        self.manifest_center.save(manifest)
        return {
            'unique': manifest['unique'],
            'duplicates': manifest['duplicates'],
            'stats': manifest['stats'],
            'structure': {
                'source_dir': self.source_dir.as_posix(),
                'output_dir': self.output_dir.as_posix(),
                'manifest_path': self.manifest_path.as_posix(),
                'total_files': manifest['stats']['total'],
                'unique_files': manifest['stats']['unique'],
                'duplicate_files': manifest['stats']['duplicates']
            }
        }