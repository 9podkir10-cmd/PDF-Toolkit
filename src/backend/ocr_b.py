import fitz
import pytesseract
from PIL import Image, ImageEnhance
from io import BytesIO
import uuid
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Any, Dict

def get_pdf_path(input_path: str) -> Optional[str]:
    path = Path(input_path)
    if path.is_file() and path.suffix.lower() == '.pdf':
        return str(path)
    elif path.is_dir():
        for p in path.rglob('*.pdf'):
            return str(p)
    return None

def get_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        application_path = Path(sys.executable).parent
    else:
        application_path = Path(__file__).resolve().parent.parent 
    
    data_path = application_path / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


class OCRBackend:
    def __init__(self, tesseract_path: str = None):
        """
        Инициализация бэкенда.
        :param tesseract_path: Путь к tesseract.exe (опционально, если не передан, берется из JSON)
        """
        self.data_root = get_data_dir()
        self.tesseract_cmd = None
        self.language = "eng"

        # 1. Если путь передан явно при создании класса - используем его
        if tesseract_path and os.path.exists(tesseract_path):
            self.tesseract_cmd = tesseract_path.replace("\\", "/")
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            print(f"[CONFIG] Tesseract path set via __init__: {self.tesseract_cmd}")
        else:
            # 2. Иначе пытаемся загрузить из settings.json
            self._load_settings()

    def _load_settings(self):
        """Загрузка настроек из JSON, если путь не передан в __init__"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
            settings_path = base_path / "backend" / "settings.json"
        else:
            current_file = Path(__file__).resolve()
            base_path = current_file.parent.parent  # src/
            settings_path = base_path / "backend" / "settings.json"

        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                ocr_path = config.get("ocr_path")
                if ocr_path and not self.tesseract_cmd: 
                    self.tesseract_cmd = ocr_path.replace("\\", "/")
                    pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                    print(f"[CONFIG] Tesseract path loaded from JSON: {self.tesseract_cmd}")

                raw_lang = config.get("language", "eng")
                self.language = self._normalize_language(raw_lang)
                print(f"[CONFIG] Language normalized to: '{self.language}' (was: '{raw_lang}')")

            except Exception as e:
                print(f"[ERROR] Не удалось прочитать settings.json: {e}")
        else:
            print(f"[WARNING] Файл настроек не найден: {settings_path}")
            self.language = "eng"

    @staticmethod
    def _normalize_language(raw: str) -> str:
        if not raw:
            return "eng"
        
        raw = str(raw).lower()
        
        if "+" in raw:
            return raw
        elif "_" in raw:
            return raw.replace("_", "+")
        else:
            # Авто-разбивка слитных строк
            if "rus" in raw and "eng" in raw:
                return "rus+eng"
            elif "rus" in raw:
                return "rus"
            elif "eng" in raw:
                return "eng"
            return raw

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        

        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.5)
        
        return enhanced

    def recognize(self, file_path: str, regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        
        if self.tesseract_cmd and not os.path.exists(self.tesseract_cmd):
            raise FileNotFoundError(f"Tesseract не найден: {self.tesseract_cmd}")

        doc = fitz.open(file_path)
        
        for i, region in enumerate(regions):
            page_num = region['page']
            rect_pdf = region['rect_pdf']
            
            fitz_page_index = page_num - 1 
            if fitz_page_index < 0 or fitz_page_index >= len(doc):
                continue
                
            page = doc[fitz_page_index]

            # Рендерим область
            pix = page.get_pixmap(clip=rect_pdf, dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(BytesIO(img_data))

            processed_img = self._preprocess_image(img)

            # Сохраняем обработанное изображение (опционально, для проверки качества)
            unique_id = uuid.uuid4().hex[:8]
            filename = f"region_{unique_id}_p{page_num}_x{region['x']}_y{region['y']}.png"
            save_path = self.data_root / filename
            processed_img.save(save_path)
            print(f"[SAVE] Изображение сохранено: {save_path}")

            try:
                text = pytesseract.image_to_string(processed_img, lang=self.language)
            except Exception as e:
                text = f"[OCR Error]: {str(e)}"

            results.append({
                "text": text.strip(),
                "image_path": str(save_path),
                "page": page_num,
                "coords": {"x": region['x'], "y": region['y'], "w": region['w'], "h": region['h']}
            })

        doc.close()
        return results



# import json
# import hashlib
# import re
# from pathlib import Path
# from datetime import datetime
# from typing import Dict, List, Optional, Any, Union
# import numpy as np
# import cv2
# import pytesseract
# import fitz  # PyMuPDF
              
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