from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QMenu, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox,
    QFileDialog, QSpinBox, QPlainTextEdit, QComboBox,
)

from gui.widgets.pdf_viewer import PDFViewer
from backend.ocr.box_to_img import PDFExtractor, Region
from backend.ocr.ocr_b import OCRBackend
from backend.ocr.storage import Storage
from backend.config import load_config, get_templates, get_selected_template_index, set_selected_template_index


class Ocr_fPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_pdf_path = None
        self.selected_rects = [] 
        self.zone_texts = []
        self.zone_ids = []   
        
        self.input_mode = None
        self.pdf_queue = []
        self.current_index = -1 

        self.extractor = PDFExtractor()
        self.storage = None
        config = load_config()
        self.ocr_storage_enabled = config.get("ocr_storage_enabled", False)
        self.ocr_backend = None

        self._build_ui()
        self._connect_signals()
        self._update_templates_combo()  
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("OCR — распознавание текста")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # Панель управления
        form = QFormLayout()
        form.setSpacing(15)

        self.input_edit = QLineEdit()
        self.input_button = QPushButton("Browse ▼")

        menu = QMenu(self)
        menu.addAction("PDF File", self._browse_file)
        menu.addAction("Folder", self._browse_folder)
        self.input_button.setMenu(menu)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)
        form.addRow("Input:", input_layout)

        main_layout.addLayout(form)

        # Основной контент
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        main_layout.addLayout(content_layout, 1)

        # Левая панель - PDF Viewer
        left_panel = QVBoxLayout()
        self.viewer = PDFViewer()
        self.viewer.rect_selected.connect(self._on_rect_selected)
        left_panel.addWidget(self.viewer)
        content_layout.addLayout(left_panel, 3)

        # Правая панель
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        # ---- ocr buttons ----
        self.ocr_button = QPushButton("Распознать выделенную область")
        self.ocr_button.setMinimumHeight(40)
        self.ocr_button.setEnabled(False)
        right_panel.addWidget(self.ocr_button)

        self.clear_button = QPushButton("Очистить выделение")
        right_panel.addWidget(self.clear_button)
        right_panel.addSpacing(20)

        # ---- Navigation panel ----
        right_panel.addWidget(QLabel("Navigation"))
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setButtonSymbols(QSpinBox.NoButtons)
        nav_layout.addWidget(self.page_spin)

        self.next_btn = QPushButton("▶")
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        right_panel.addLayout(nav_layout)

        self.page_info = QLabel("Страница 1 из 1")
        self.page_info.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(self.page_info)
        right_panel.addSpacing(15)

        # ---- результат распознавания ----
        self.ocr_info = QLabel("Выделено областей: 0")
        right_panel.addWidget(self.ocr_info)
        self.result_text = QPlainTextEdit()
        self.result_text.setFixedHeight(260)
        right_panel.addWidget(self.result_text)

        # ---- Rename templates ----
        right_panel.addWidget(QLabel("Шаблон переименования:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("Не использовать", -1)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        right_panel.addWidget(self.template_combo)

        # ---- имя файла ----
        right_panel.addWidget(QLabel("Имя файла"))
        self.filename_edit = QLineEdit()
        right_panel.addWidget(self.filename_edit)

        right_panel.addStretch()

        # ---- Apply button ----
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setMinimumHeight(42)
        right_panel.addWidget(self.apply_btn)

        content_layout.addLayout(right_panel, 2)

        main_layout.addStretch()

    def _connect_signals(self):
        self.input_edit.textChanged.connect(self._on_path_changed)
        self.ocr_button.clicked.connect(self._run_ocr)
        self.clear_button.clicked.connect(self._clear_selection)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        self.page_spin.valueChanged.connect(self._change_page)
        self.apply_btn.clicked.connect(self._apply_action)

    # ---------- Навигация и загрузка ----------
    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf)"
        )
        if filename:
            self.input_edit.setText(filename)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")

        if directory:
            self.input_mode = "folder"

            self.pdf_queue = sorted(
                str(p) for p in Path(directory).rglob("*.pdf")
            )

            if not self.pdf_queue:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "В папке нет PDF файлов"
                )
                return

            self.current_index = 0

            self.input_edit.setText(directory)

            self._load_pdf(self.pdf_queue[0])
            
    def _update_templates_combo(self):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("Не использовать", -1)
        templates = get_templates()
        for idx, pattern in enumerate(templates):
            self.template_combo.addItem(pattern, idx)
        selected_idx = get_selected_template_index()
        found = -1
        for i in range(self.template_combo.count()):
            if self.template_combo.itemData(i) == selected_idx:
                found = i
                break
        self.template_combo.setCurrentIndex(found if found >= 0 else 0)
        self.template_combo.blockSignals(False)

    def _on_template_changed(self, index):
        set_selected_template_index(self.template_combo.currentData())                
                      
    def _get_storage(self):
        if self.storage is None and self.ocr_storage_enabled:
            storage_path = Path("ocr_storage")
            storage_path.mkdir(exist_ok=True)
            self.storage = Storage(storage_path)
        return self.storage

    def _load_pdf(self, pdf_path):
        if not pdf_path:
            return

        self.current_pdf_path = pdf_path

        self.viewer.load_pdf(pdf_path, 0)

        self.selected_rects = []
        self.ocr_results = []
        self.zone_texts = [] 
        
        self.ocr_info.setText("Выделено областей: 0")
        self.result_text.clear()
        self.filename_edit.setText(Path(pdf_path).stem)        

        total_pages = self.viewer.get_total_pages()
        self.page_spin.setMaximum(total_pages if total_pages else 1)
        self.page_spin.setValue(1)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(total_pages > 1)
        self.page_info.setText(f"Страница 1 из {total_pages}")
        self.ocr_button.setEnabled(False)
        self.result_text.setPlainText(f"PDF загружен:\n{pdf_path}")

    def _on_path_changed(self, path: str):

        if not path.strip():
            return

        p = Path(path)

        if p.is_file():
            self.input_mode = "file"
            self.pdf_queue = []
            self.current_index = -1

            self._load_pdf(str(p))
            return


        if p.is_dir():

            self.input_mode = "folder"

            self.pdf_queue = sorted(
                str(x) for x in p.rglob("*.pdf")
            )

            if self.pdf_queue:
                self.current_index = 0
                self._load_pdf(
                    self.pdf_queue[0]
                )
            else:
                self.result_text.setPlainText(
                    "PDF не найден"
                )

    def _get_pdf_path(self, input_path: str):
        path = Path(input_path)
        if path.is_file() and path.suffix.lower() == '.pdf':
            return str(path)
        elif path.is_dir():
            for p in path.rglob('*.pdf'):
                return str(p)
        return None

    def _change_page(self, page_num: int):
        if hasattr(self, '_changing_page') and self._changing_page:
            return
        self._changing_page = True
        try:
            self.viewer.go_to_page(page_num - 1)
            self.viewer.clear_selection()
            self.selected_rects = [] 
            self.ocr_button.setEnabled(False)
            total_pages = self.page_spin.maximum()
            self.prev_btn.setEnabled(page_num > 1)
            self.next_btn.setEnabled(page_num < total_pages)
            self.page_info.setText(f"Страница {page_num} из {total_pages}")
        finally:
            self._changing_page = False

    def _prev_page(self):
        current = self.page_spin.value()
        if current > 1:
            self.page_spin.setValue(current - 1)

    def _next_page(self):
        current = self.page_spin.value()
        if current < self.page_spin.maximum():
            self.page_spin.setValue(current + 1)

    # ---------- Выделение областей ----------
    def _on_rect_selected(self, x, y, w, h, page):
        new_rect = (x, y, w, h, page)
        self.selected_rects.append(new_rect)
        count = len(self.selected_rects)
        self.ocr_info.setText(f"Выделено областей: {count}")
        self.ocr_button.setEnabled(count > 0)
        zone_index = count - 1
        self.result_text.appendPlainText(f"zone{zone_index}: {new_rect}")

    def _clear_selection(self):
        self.viewer.clear_selection()
        self.selected_rects = []
        self.zone_texts = []
        self.zone_ids.clear()
        self.ocr_info.setText("Выделено областей: 0")
        self.ocr_button.setEnabled(False)

    # ---------- Основной OCR ----------
    def _run_ocr(self):
        config = load_config()
        self.ocr_storage_enabled = config.get("ocr_storage_enabled", False)
        
        if not self.ocr_storage_enabled and self.storage is not None:
            self.storage = None
        
        if self.ocr_backend is None:
            try:
                config = load_config()
                self.ocr_backend = OCRBackend(
                    tesseract_path=config.get("ocr_path", ""),
                    language=config.get("language", "rus+eng")
                )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка OCR", str(e) + "\nУкажите путь к Tesseract в settings.json")
                return
        
        if not self.current_pdf_path or not self.selected_rects:
            QMessageBox.warning(self, "Ошибка", "Не выбран PDF или не выделена область.")
            return

        if self.ocr_backend is not None:
            try:
                self.ocr_backend.reload_from_config()
            except FileNotFoundError as e:
                QMessageBox.critical(self, "Ошибка OCR", str(e))
                return

        self.result_text.clear()
        self.zone_texts = []               
        dpi = getattr(self.viewer, 'dpi', 300)

        for (x, y, w, h, page) in self.selected_rects:
            try:
                pdf_x = x / dpi * 72
                pdf_y = y / dpi * 72
                pdf_w = w / dpi * 72
                pdf_h = h / dpi * 72

                if pdf_w <= 0 or pdf_h <= 0:
                    self.result_text.appendPlainText(f"Пропущена область с нулевым размером: ({x}, {y}) {w}x{h}")
                    self.zone_texts.append("")  
                    continue

                region = Region(page=page + 1, x=pdf_x, y=pdf_y, w=pdf_w, h=pdf_h)
                image = self.extractor.crop_region(self.current_pdf_path, region, dpi=dpi )

                if image is None or image.size[0] == 0 or image.size[1] == 0:
                    self.result_text.appendPlainText(f"Пустое изображение для области ({x}, {y})")
                    self.zone_texts.append("")                          
                    continue

                if self.ocr_backend is None:
                    self.result_text.appendPlainText("OCR не инициализирован.")
                    return

                text = self.ocr_backend.recognize(image)
                clean_text = text.strip()
                self.zone_texts.append(clean_text)
                zone_index = len(self.zone_texts) - 1
                self.result_text.appendPlainText(f"{{zone{zone_index}}} {clean_text}")
                
                storage = self._get_storage()
                if storage is not None:
                    image_id = storage.save_image(
                        image=image,
                        pdf_path=self.current_pdf_path,
                        page=page + 1,
                        coords={"x": x, "y": y, "w": w, "h": h},
                        ocr_text=text
                    )
                    self.zone_ids.append(image_id)
                else:
                    self.zone_ids.append(None)

            except Exception as e:
                import traceback
                error_text = f"Ошибка при обработке области {x},{y}: {str(e)}\n{traceback.format_exc()}"
                self.result_text.appendPlainText(error_text)
                self.zone_texts.append("") 

    def _apply_action(self):
        if not self.current_pdf_path:
            return

        if hasattr(self.viewer, 'close_document'):
            self.viewer.close_document()
        else:
            try:
                self.viewer.load_pdf(None)
            except:
                pass

        old_file = Path(self.current_pdf_path)

        # --- 1. Парсинг исправлений из поля результата ---
        current_text = self.result_text.toPlainText()
        lines = current_text.splitlines()
        storage = self._get_storage()
        import re
        pattern_zone = re.compile(r'\{zone(\d+)\}\s*(.*)')
        updates = {}
        for line in lines:
            match = pattern_zone.match(line)
            if match:
                idx = int(match.group(1))
                txt = match.group(2)
                updates[idx] = txt

        # Применяем изменения к zone_texts и в storage
        for idx, new_txt in updates.items():
            if 0 <= idx < len(self.zone_texts):
                if new_txt != self.zone_texts[idx]:
                    self.zone_texts[idx] = new_txt
                    if storage is not None and idx < len(self.zone_ids) and self.zone_ids[idx] is not None:
                        try:
                            storage.update_text(self.zone_ids[idx], new_txt, is_correction=True)
                        except ValueError:
                            pass  # игнорируем, если id не найден

        # --- 2. Формирование нового имени ---
        selected_idx = get_selected_template_index()
        new_name = None

        if selected_idx >= 0:
            templates = get_templates()
            if selected_idx < len(templates):
                pattern = templates[selected_idx]
                # Проверяем наличие плейсхолдеров в шаблоне
                placeholders = re.findall(r'\{zone(\d+)\}', pattern)
                if placeholders:
                    # Если есть плейсхолдеры, проверяем, что зоны существуют
                    if not self.zone_texts:
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            "Нет распознанных зон для подстановки в шаблон."
                        )
                        return
                    if len(set(placeholders)) != len(self.zone_texts):
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            f"Шаблон требует: {len(set(placeholders))}, но распознано {len(self.zone_texts)} зон."
                        )
                        return
                # Подстановка текстов в шаблон
                for i, text in enumerate(self.zone_texts):
                    placeholder = f"{{zone{i}}}"
                    if placeholder in pattern:
                        pattern = pattern.replace(placeholder, text)
                new_name = pattern
            else:
                # Если индекс некорректен, сбрасываем выбор
                set_selected_template_index(-1)
                new_name = self.filename_edit.text().strip()
        else:
            new_name = self.filename_edit.text().strip()

        # Если имя не задано, оставляем старое
        if not new_name:
            new_name = old_file.stem

        # --- 3. Переименование ---
        if new_name != old_file.stem:
            if not new_name.lower().endswith(".pdf"):
                new_name += ".pdf"
            new_file = old_file.parent / new_name
            try:
                old_file.rename(new_file)
                self.current_pdf_path = str(new_file)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать файл:\n{e}")
                return

        # --- 4. Переход к следующему PDF (если папка) ---
        if self.input_mode == "folder":
            self.current_index += 1
            if self.current_index < len(self.pdf_queue):
                next_pdf = self.pdf_queue[self.current_index]
                self._load_pdf(next_pdf)
            else:
                self._reset_state()
                QMessageBox.information(self, "Готово", "Все PDF обработаны")


    def _reset_state(self):
        self.current_pdf_path = None
        self.pdf_queue = []
        self.current_index = -1
        self.input_mode = None

        self.selected_rects.clear()
        self.ocr_results.clear()
        self.zone_texts.clear()
        self.zone_ids.clear()

        self.input_edit.blockSignals(True)
        self.input_edit.clear()
        self.input_edit.blockSignals(False)

        self.filename_edit.clear()

        if hasattr(self.viewer, "close_document"):
            try:
                self.viewer.close_document()
            except Exception:
                pass

        self.viewer.clear_selection()

        self.result_text.clear()

        self.ocr_info.setText(
            "Выделено областей: 0"
        )

        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)

        self.page_info.setText(
            "Страница 1 из 1"
        )

        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        self.ocr_button.setEnabled(False)