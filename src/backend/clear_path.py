from pathlib import Path
from typing import List, Dict
import os
import shutil
import hashlib
from datetime import datetime

class DirectoryNormalizer:
    def __init__(self, source_dir: str, output_dir: str = None):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir) if output_dir else self.source_dir.parent / "output"
        self.work_dir = self.output_dir / "WORK"
        self.results_dir = self.output_dir / "ИТОГИ"
        self.check_dir = self.output_dir / "ПРОВЕРКА"
        
        self._cleanup_output_dir()
        self._create_directory_structure()
    
    def _cleanup_output_dir(self):
        if self.output_dir.exists():
            delete_dir = self.output_dir.parent / f"delete_this_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(self.output_dir), str(delete_dir))
    
    def _create_directory_structure(self):
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.check_dir.mkdir(parents=True, exist_ok=True)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _get_unique_filename(self, original_name: str, counter: int) -> str:
        name, ext = os.path.splitext(original_name)
        return f"{name}_{counter}{ext}" if counter > 0 else f"{name}{ext}"
    
    def discover_all_pdfs(self) -> List[Dict]:
        pdf_files = []
        seen_hashes = set()
        
        for pdf_path in self.source_dir.rglob("*.pdf"):
            if pdf_path.suffix.lower() == '.pdf' and pdf_path.is_file():
                try:
                    if self.output_dir in pdf_path.parents:
                        continue
                    
                    file_size = pdf_path.stat().st_size
                    if file_size == 0:
                        continue
                    
                    file_hash = self._calculate_file_hash(pdf_path)
                    
                    file_info = {
                        'original_path': str(pdf_path),
                        'original_name': pdf_path.name,
                        'original_parent': pdf_path.parent.name,
                        'relative_path': str(pdf_path.relative_to(self.source_dir)),
                        'file_size': file_size,
                        'file_hash': file_hash,
                        'status': 'found'
                    }
                    
                    if file_hash and file_hash in seen_hashes:
                        file_info['status'] = 'duplicate'
                    else:
                        seen_hashes.add(file_hash)
                    
                    pdf_files.append(file_info)
                except Exception:
                    continue
        
        return pdf_files
    
    def normalize_structure(self) -> Dict:
        pdf_files = self.discover_all_pdfs()
        
        if not pdf_files:
            return {'files': [], 'stats': {'success': 0, 'duplicates': 0, 'errors': 0}}
        
        normalized_files = []
        stats = {'success': 0, 'duplicates': 0, 'errors': 0}
        doc_counter = 1
        dup_counter = 1
        duplicate_map = {}
        
        for file_info in pdf_files:
            try:
                if file_info['status'] == 'duplicate':
                    dup_id = f"dup_{dup_counter}"
                    dup_folder = self.check_dir / dup_id
                    dup_folder.mkdir(exist_ok=True)
                    
                    original_id = None
                    for norm_file in normalized_files:
                        if (norm_file.get('file_hash') == file_info['file_hash'] and 
                            norm_file['status'] == 'normalized'):
                            original_id = norm_file['doc_id']
                            break
                    
                    if original_id:
                        duplicate_map[dup_id] = original_id
                    
                    target_pdf = dup_folder / file_info['original_name']
                    copy_counter = 0
                    while target_pdf.exists():
                        copy_counter += 1
                        new_name = self._get_unique_filename(file_info['original_name'], copy_counter)
                        target_pdf = dup_folder / new_name
                    
                    shutil.copy2(file_info['original_path'], target_pdf)
                    
                    normalized_files.append({
                        **file_info,
                        'doc_id': dup_id,
                        'work_folder': str(dup_folder),
                        'work_pdf_path': str(target_pdf),
                        'status': 'duplicate',
                        'original_doc_id': original_id
                    })
                    stats['duplicates'] += 1
                    dup_counter += 1
                else:
                    doc_id = f"doc_{doc_counter}"
                    doc_folder = self.work_dir / doc_id
                    doc_folder.mkdir(exist_ok=True)
                    
                    target_pdf = doc_folder / file_info['original_name']
                    copy_counter = 0
                    while target_pdf.exists():
                        copy_counter += 1
                        new_name = self._get_unique_filename(file_info['original_name'], copy_counter)
                        target_pdf = doc_folder / new_name
                    
                    shutil.copy2(file_info['original_path'], target_pdf)
                    
                    normalized_files.append({
                        **file_info,
                        'doc_id': doc_id,
                        'work_folder': str(doc_folder),
                        'work_pdf_path': str(target_pdf),
                        'status': 'normalized'
                    })
                    stats['success'] += 1
                    doc_counter += 1
            except Exception:
                stats['errors'] += 1
        
        self._save_reports(normalized_files, stats, duplicate_map)
        
        return {
            'files': normalized_files,
            'stats': stats,
            'structure': {
                'work_dir': str(self.work_dir),
                'check_dir': str(self.check_dir),
                'results_dir': str(self.results_dir),
                'total_work_folders': stats['success'],
                'total_duplicate_folders': stats['duplicates']
            }
        }
    
    def _save_reports(self, files: List[Dict], stats: Dict, duplicates_map: Dict):
        report_path = self.results_dir / "normalization_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Source: {self.source_dir}\n")
            f.write(f"Output: {self.output_dir}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Success: {stats['success']}\n")
            f.write(f"Duplicates: {stats['duplicates']}\n")
            f.write(f"Errors: {stats['errors']}\n")
            f.write(f"Total: {len(files)}\n\n")
            
            for file_info in files:
                f.write(f"{file_info['doc_id']} | {file_info['original_name']} | {file_info['status']}\n")