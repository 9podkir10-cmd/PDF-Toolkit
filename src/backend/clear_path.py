from pathlib import Path
from typing import List, Dict, Optional, Tuple
import os
import shutil
import hashlib
from datetime import datetime
import re
import json
import cv2
import pytesseract
import fitz
import numpy as np

class DirectoryNormalizer:
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = self.source_dir.parent / f"{self.source_dir.name}_hardlink"
        self.manifest_path = self.output_dir / "manifest.json"
        
        self._validate_and_prepare()
        self._create_directory_structure()
    
    def _validate_and_prepare(self):
        has_pdfs = any(self.source_dir.rglob("*.pdf"))
        output_exists = self.output_dir.exists()
        
        if not has_pdfs:
            raise Exception(f"В папке {self.source_dir} нет PDF файлов!")
        
        if output_exists:
            raise Exception(f"Папка {self.output_dir} уже существует! Hardlink нельзя запускать повторно.")
    
    def _create_directory_structure(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _calculate_file_hash(self, file_path: Path, bytes_count: int = None) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                if bytes_count:
                    chunk = f.read(bytes_count)
                    hash_md5.update(chunk)
                else:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _compare_byte_by_byte(self, file1_path: Path, file2_path: Path) -> bool:
        try:
            with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
                while True:
                    chunk1 = f1.read(8192)
                    chunk2 = f2.read(8192)
                    
                    if len(chunk1) != len(chunk2):
                        return False
                    
                    if chunk1 != chunk2:
                        return False
                    
                    if not chunk1:
                        return True
        except Exception:
            return False
    
    def _create_hardlink(self, source_path: Path, target_path: Path):
        if target_path.exists():
            counter = 1
            while True:
                new_target = target_path.parent / f"{target_path.stem}_{counter}{target_path.suffix}"
                if not new_target.exists():
                    target_path = new_target
                    break
                counter += 1
        os.link(source_path, target_path)
        return target_path
    
    def _get_name_without_extension(self, file_path: Path) -> str:
        return file_path.stem
    
    def discover_all_pdfs(self) -> List[Dict]:
        pdf_files = []
        
        for pdf_path in self.source_dir.rglob("*.pdf"):
            if pdf_path.suffix.lower() == '.pdf' and pdf_path.is_file():
                try:
                    if self.output_dir in pdf_path.parents:
                        continue
                    
                    file_size = pdf_path.stat().st_size
                    if file_size == 0:
                        continue
                    
                    pdf_files.append({
                        'path': pdf_path,
                        'name': pdf_path.name,
                        'name_without_ext': pdf_path.stem,
                        'size': file_size,
                        'parent': pdf_path.parent.name,
                        'relative_path': str(pdf_path.relative_to(self.source_dir))
                    })
                except Exception:
                    continue
        
        return pdf_files
    
    def normalize_structure(self) -> Dict:
        pdf_files = self.discover_all_pdfs()
        
        if not pdf_files:
            return {'files': {}, 'stats': {'total': 0, 'unique': 0, 'duplicates': 0, 'errors': 0}}
        
        manifest = {
            'source_dir': self.source_dir.as_posix(),
            'output_dir': self.output_dir.as_posix(),
            'created_at': datetime.now().isoformat(),
            'files': {}
        }
        
        stats = {'total': len(pdf_files), 'unique': 0, 'duplicates': 0, 'errors': 0}
        
        # Этап 1: Группировка по размеру (точные байты)
        size_groups = {}
        for file_info in pdf_files:
            size_key = str(file_info['size'])
            if size_key not in size_groups:
                size_groups[size_key] = []
            size_groups[size_key].append(file_info)
        
        # Этап 2: Группировка по частичному хешу (первые 4096 байт)
        partial_hash_groups = {}
        for size_key, files in size_groups.items():
            if len(files) == 1:
                file_info = files[0]
                new_name = f"{file_info['name_without_ext']}_{file_info['size']}B.pdf"
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                
                manifest['files'][new_name] = {
                    'old_name': file_info['name'],
                    'new_name': new_name,
                    'original_path': file_info['path'].as_posix(),
                    'hash': None,
                    'size': file_info['size'],
                    'is_duplicate': False,
                    'stage': 1
                }
                stats['unique'] += 1
            else:
                for file_info in files:
                    partial_hash = self._calculate_file_hash(file_info['path'], 4096)
                    if not partial_hash:
                        continue
                    key = f"{size_key}_{partial_hash}"
                    if key not in partial_hash_groups:
                        partial_hash_groups[key] = []
                    partial_hash_groups[key].append(file_info)
        
        # Этап 3: Группировка по полному хешу
        full_hash_groups = {}
        for key, files in partial_hash_groups.items():
            if len(files) == 1:
                file_info = files[0]
                new_name = f"{file_info['name_without_ext']}_{file_info['size']}B_{key.split('_')[1]}.pdf"
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                
                manifest['files'][new_name] = {
                    'old_name': file_info['name'],
                    'new_name': new_name,
                    'original_path': file_info['path'].as_posix(),
                    'hash': None,
                    'size': file_info['size'],
                    'is_duplicate': False,
                    'stage': 2
                }
                stats['unique'] += 1
            else:
                for file_info in files:
                    full_hash = self._calculate_file_hash(file_info['path'])
                    if not full_hash:
                        continue
                    if full_hash not in full_hash_groups:
                        full_hash_groups[full_hash] = []
                    full_hash_groups[full_hash].append(file_info)
        
        # Этап 4: Побайтовое сравнение
        for full_hash, files in full_hash_groups.items():
            if len(files) == 1:
                file_info = files[0]
                new_name = f"{full_hash}.pdf"
                target_path = self.output_dir / new_name
                self._create_hardlink(file_info['path'], target_path)
                
                manifest['files'][new_name] = {
                    'old_name': file_info['name'],
                    'new_name': new_name,
                    'original_path': file_info['path'].as_posix(),
                    'hash': full_hash,
                    'size': file_info['size'],
                    'is_duplicate': False,
                    'stage': 3
                }
                stats['unique'] += 1
            else:
                # Побайтовое сравнение файлов с одинаковым хешем
                unique_files = []
                duplicate_pairs = []
                
                for i, file_info in enumerate(files):
                    is_duplicate = False
                    
                    for unique_file in unique_files:
                        if self._compare_byte_by_byte(file_info['path'], unique_file['path']):
                            is_duplicate = True
                            duplicate_pairs.append((file_info, unique_file))
                            break
                    
                    if not is_duplicate:
                        unique_files.append(file_info)
                
                # Обработка уникальных файлов
                for file_info in unique_files:
                    new_name = f"{full_hash}.pdf"
                    target_path = self.output_dir / new_name
                    
                    counter = 0
                    while target_path.exists():
                        counter += 1
                        new_name = f"{full_hash}_{counter}.pdf"
                        target_path = self.output_dir / new_name
                    
                    self._create_hardlink(file_info['path'], target_path)
                    
                    manifest['files'][new_name] = {
                        'old_name': file_info['name'],
                        'new_name': new_name,
                        'original_path': file_info['path'].as_posix(),
                        'hash': full_hash,
                        'size': file_info['size'],
                        'is_duplicate': False,
                        'stage': 4,
                        'linked_files': []
                    }
                    stats['unique'] += 1
                    
                    file_info['unique_name'] = new_name
                
                # Обработка дубликатов
                for file_info, original_file in duplicate_pairs:
                    original_name = None
                    for uf in unique_files:
                        if uf['path'] == original_file['path']:
                            original_name = uf.get('unique_name')
                            break
                    
                    if original_name and original_name in manifest['files']:
                        dup_counter = len(manifest['files'][original_name]['linked_files']) + 1
                        dup_name = f"{full_hash}_dup{dup_counter}.pdf"
                        target_path = self.output_dir / dup_name
                        self._create_hardlink(file_info['path'], target_path)
                        
                        manifest['files'][dup_name] = {
                            'old_name': file_info['name'],
                            'new_name': dup_name,
                            'original_path': file_info['path'].as_posix(),
                            'hash': full_hash,
                            'size': file_info['size'],
                            'is_duplicate': True,
                            'stage': 4,
                            'links_to': original_name
                        }
                        manifest['files'][original_name]['linked_files'].append(dup_name)
                        stats['duplicates'] += 1
        
        self._save_manifest(manifest)
        
        return {
            'files': manifest['files'],
            'stats': stats,
            'structure': {
                'source_dir': self.source_dir.as_posix(),
                'output_dir': self.output_dir.as_posix(),
                'manifest_path': self.manifest_path.as_posix(),
                'total_files': stats['total'],
                'unique_files': stats['unique'],
                'duplicate_files': stats['duplicates']
            }
        }
    
    def _save_manifest(self, manifest: Dict):
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
                
# pytesseract.pytesseract.tesseract_cmd = r'C:\Users\User\OneDrive\Desktop\pod\PDF Toolkit\Tesseract-OCR\tesseract.exe'


# class RegionTemplate:
#     def __init__(self, template_id: str, doc_type: str, region: Dict, confidence: float = 1.0):
#         self.template_id = template_id
#         self.doc_type = doc_type
#         self.region = region
#         self.confidence = confidence
#         self.usage_count = 0
#         self.last_used = datetime.now().isoformat()
#         self.success_rate = 1.0

#     def to_dict(self):
#         return {
#             'template_id': self.template_id,
#             'doc_type': self.doc_type,
#             'region': self.region,
#             'confidence': self.confidence,
#             'usage_count': self.usage_count,
#             'last_used': self.last_used,
#             'success_rate': self.success_rate
#         }

#     @classmethod
#     def from_dict(cls, data):
#         template = cls(
#             data['template_id'],
#             data['doc_type'],
#             data['region'],
#             data['confidence']
#         )
#         template.usage_count = data.get('usage_count', 0)
#         template.last_used = data.get('last_used', datetime.now().isoformat())
#         template.success_rate = data.get('success_rate', 1.0)
#         return template


# class RegionManager:
#     def __init__(self, templates_path: Path = None):
#         self.templates_path = templates_path or Path("config/region_templates.json")
#         self.history_path = self.templates_path.parent / "extraction_history.json"
#         self.templates: Dict[str, RegionTemplate] = {}
#         self.history: List[Dict] = []
#         self.load_templates()
#         self.load_history()

#     def load_templates(self):
#         if self.templates_path.exists():
#             try:
#                 with open(self.templates_path, 'r', encoding='utf-8') as f:
#                     data = json.load(f)
#                     for template_data in data.get('templates', []):
#                         template = RegionTemplate.from_dict(template_data)
#                         self.templates[template.template_id] = template
#             except Exception as e:
#                 print(f"Ошибка загрузки шаблонов: {e}")

#     def save_templates(self):
#         self.templates_path.parent.mkdir(parents=True, exist_ok=True)
#         data = {
#             'templates': [t.to_dict() for t in self.templates.values()],
#             'updated_at': datetime.now().isoformat()
#         }
#         with open(self.templates_path, 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)

#     def load_history(self):
#         if self.history_path.exists():
#             try:
#                 with open(self.history_path, 'r', encoding='utf-8') as f:
#                     self.history = json.load(f)
#             except Exception as e:
#                 print(f"Ошибка загрузки истории: {e}")

#     def save_history(self):
#         self.history_path.parent.mkdir(parents=True, exist_ok=True)
#         with open(self.history_path, 'w', encoding='utf-8') as f:
#             json.dump(self.history, f, ensure_ascii=False, indent=2)

#     def get_document_signature(self, pdf_path: str) -> str:
#         pdf_path = Path(pdf_path)
#         if not pdf_path.exists():
#             return ""
#         with open(pdf_path, 'rb') as f:
#             content = f.read(4096)
#             return hashlib.md5(content).hexdigest()[:16]

#     def find_template(self, pdf_path: str) -> Optional[RegionTemplate]:
#         signature = self.get_document_signature(pdf_path)
#         for template in self.templates.values():
#             if template.doc_type == signature:
#                 return template
#         return None

#     def get_region(self, pdf_path: str, markers: Dict = None) -> Optional[Dict]:
#         template = self.find_template(pdf_path)
#         if template and template.confidence > 0.7:
#             return template.region
#         return None

#     def add_or_update_template(self, pdf_path: str, region: Dict, success: bool = True):
#         signature = self.get_document_signature(pdf_path)
        
#         template = self.find_template(pdf_path)
#         if template:
#             template.region = region
#             template.usage_count += 1
#             template.last_used = datetime.now().isoformat()
#             if success:
#                 template.success_rate = (template.success_rate * (template.usage_count - 1) + 1) / template.usage_count
#             else:
#                 template.success_rate = (template.success_rate * (template.usage_count - 1)) / template.usage_count
#         else:
#             template_id = f"template_{len(self.templates) + 1}"
#             template = RegionTemplate(template_id, signature, region)
#             template.usage_count = 1
#             template.success_rate = 1.0 if success else 0.0
#             self.templates[template_id] = template
        
#         self.save_templates()

#     def add_to_history(self, pdf_path: str, region: Dict, result: Dict):
#         entry = {
#             'pdf': str(pdf_path),
#             'region': region,
#             'result': result,
#             'timestamp': datetime.now().isoformat(),
#             'signature': self.get_document_signature(pdf_path)
#         }
#         self.history.append(entry)
#         if len(self.history) > 1000:
#             self.history = self.history[-1000:]
#         self.save_history()

# class OCRProvider:
#     def __init__(self, tesseract_path: str = None):
#         if tesseract_path:
#             pytesseract.pytesseract.tesseract_cmd = tesseract_path

#     def extract_text(self, image) -> str:
#         processed = self._preprocess_image(image)
#         return pytesseract.image_to_string(processed, lang='rus+eng')

#     def _preprocess_image(self, image):
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         return cv2.convertScaleAbs(gray, alpha=1.5, beta=0)


# class PDFProcessor:
#     def __init__(self, ocr: OCRProvider = None):
#         self.ocr = ocr or OCRProvider()

#     def pdf_to_images(self, pdf_path: str, dpi: int = 300, pages: List[int] = None) -> List[np.ndarray]:
#         try:
#             doc = fitz.open(pdf_path)
#             images = []
            
#             page_range = pages if pages else range(len(doc))
#             for page_num in page_range:
#                 if isinstance(page_num, int) and page_num >= len(doc):
#                     continue
#                 page = doc.load_page(page_num)
#                 mat = fitz.Matrix(dpi/72, dpi/72)
#                 pix = page.get_pixmap(matrix=mat)
                
#                 img_data = pix.tobytes("png")
#                 img_array = np.frombuffer(img_data, np.uint8)
#                 img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
#                 images.append(img)
            
#             doc.close()
#             return images
#         except Exception as e:
#             print(f"Ошибка при конвертации PDF: {e}")
#             return []

#     def extract_text_from_pdf(self, pdf_path: str, pages: List[int] = None) -> Optional[str]:
#         try:
#             images = self.pdf_to_images(pdf_path, dpi=300, pages=pages)
#             if not images:
#                 return None
            
#             full_text = ""
#             for i, image in enumerate(images):
#                 text = self.ocr.extract_text(image)
#                 full_text += f"\n--- Страница {i+1} ---\n{text}"
            
#             return full_text
#         except Exception as e:
#             print(f"Ошибка при обработке {pdf_path}: {e}")
#             return None

#     def extract_text_from_region(self, pdf_path: str, region: Dict) -> Optional[str]:
#         try:
#             page_num = region.get('page', 0)
#             images = self.pdf_to_images(pdf_path, dpi=300, pages=[page_num])
#             if not images:
#                 return None
            
#             image = images[0]
#             x, y, w, h = region.get('x', 0), region.get('y', 0), region.get('w', 0), region.get('h', 0)
            
#             if w > 0 and h > 0:
#                 cropped = image[y:y+h, x:x+w]
#             else:
#                 cropped = image
            
#             text = self.ocr.extract_text(cropped)
#             return text.strip()
#         except Exception as e:
#             print(f"Ошибка извлечения из области: {e}")
#             return None


# class RegionExtractor:
#     def __init__(self):
#         self.region_manager = RegionManager()
#         self.pdf_processor = PDFProcessor()
#         self.learning_mode = True

#     def extract(self, pdf_path: str, markers: Dict = None, interactive: bool = True) -> Dict:
#         result = {
#             'pdf_path': str(pdf_path),
#             'success': False,
#             'text': None,
#             'region_used': None,
#             'method': 'unknown',
#             'confidence': 0
#         }

#         region = self.region_manager.get_region(pdf_path, markers)
        
#         if region:
#             text = self.pdf_processor.extract_text_from_region(pdf_path, region)
#             if text:
#                 result['success'] = True
#                 result['text'] = text
#                 result['region_used'] = region
#                 result['method'] = 'template'
#                 result['confidence'] = 0.9
                
#                 if self.learning_mode:
#                     self.region_manager.add_to_history(pdf_path, region, result)
#                     self.region_manager.add_or_update_template(pdf_path, region, True)
                
#                 return result

#         if interactive:
#             region = self._get_manual_region(pdf_path)
#             if region:
#                 text = self.pdf_processor.extract_text_from_region(pdf_path, region)
#                 if text:
#                     result['success'] = True
#                     result['text'] = text
#                     result['region_used'] = region
#                     result['method'] = 'manual'
#                     result['confidence'] = 1.0
                    
#                     if self.learning_mode:
#                         self.region_manager.add_to_history(pdf_path, region, result)
#                         self.region_manager.add_or_update_template(pdf_path, region, True)
                    
#                     return result

#         preview_text = self.pdf_processor.extract_text_from_pdf(pdf_path, pages=[0, 1])
#         if preview_text and markers:
#             extracted = self._extract_with_markers(preview_text, markers)
#             if extracted:
#                 result['success'] = True
#                 result['text'] = extracted
#                 result['method'] = 'markers'
#                 result['confidence'] = 0.7
#                 return result

#         return result

#     def _get_manual_region(self, pdf_path: str) -> Optional[Dict]:
#         print(f"\n=== РУЧНОЙ ВЫБОР ОБЛАСТИ ===")
#         print(f"Файл: {pdf_path}")
#         print("Введите координаты области или используйте графический интерфейс")
        
#         try:
#             x = int(input("X координата (лево): "))
#             y = int(input("Y координата (верх): "))
#             w = int(input("Ширина области: "))
#             h = int(input("Высота области: "))
#             page = int(input("Номер страницы (0 для первой): "))
            
#             return {'x': x, 'y': y, 'w': w, 'h': h, 'page': page}
#         except:
#             print("Ошибка ввода координат")
#             return None

#     def _extract_with_markers(self, text: str, markers: Dict) -> Optional[str]:
#         opening = markers.get('opening', '')
#         closing = markers.get('closing', '')
        
#         if not opening and not closing:
#             return text
        
#         try:
#             start_pos = 0
#             if opening:
#                 opening_escaped = re.escape(opening)
#                 start_match = re.search(opening_escaped, text, re.IGNORECASE)
#                 if start_match:
#                     start_pos = start_match.end()
            
#             end_pos = len(text)
#             if closing:
#                 closing_escaped = re.escape(closing)
#                 end_match = re.search(closing_escaped, text[start_pos:], re.IGNORECASE)
#                 if end_match:
#                     end_pos = start_pos + end_match.start()
            
#             extracted = text[start_pos:end_pos].strip()
#             return extracted if extracted else None
#         except:
#             return None

#     def extract_batch(self, folder_path: str, markers: Dict = None, interactive: bool = True) -> List[Dict]:
#         results = []
#         pdf_files = list(Path(folder_path).rglob("*.pdf"))
        
#         for pdf_file in pdf_files:
#             result = self.extract(str(pdf_file), markers, interactive)
#             results.append(result)
#             print(f"{'✓' if result['success'] else '✗'} {pdf_file.name}")
        
#         return results