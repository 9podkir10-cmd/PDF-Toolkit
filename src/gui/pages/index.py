from pathlib import Path
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QWidget, QLabel, QMenu, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox, QCheckBox,
    QFileDialog, QSpinBox, QPlainTextEdit, QComboBox,
)

from backend.services.queue_service import PDFQueueService
from backend.services.file_workflow import PDFFileWorkflow
from backend.services.ocr_workflow import OCRWorkflow
from backend.services.template_service import FilenameTemplateService
from gui.widgets.pdf_viewer import PDFViewer
from gui.widgets.models import OCRSession
from gui.workers.ocr_worker import OCRWorker
from gui.signals import app_signals
from backend.structure import preview_structure, structure_pdfs 
from backend.services.box_to_img import PDFExtractor, Region
from backend.services.ocr_b import OCRBackend
from backend.clear_path import DirectoryNormalizer
from backend.config import load_config, get_templates, get_selected_template_index, set_selected_template_index


class Ocr_fPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = OCRSession() 
        self._ocr_running = False
        self._ocr_thread = None
        self._ocr_worker = None

        self.queue_service = PDFQueueService()
        self.template_service = FilenameTemplateService()
        self.file_workflow = PDFFileWorkflow(self.template_service)

        config = load_config()
        tesseract_path = config.get("ocr_path", None)
        language = config.get("language", "rus+eng")

        ocr_backend = OCRBackend(tesseract_path, language)

        self.ocr_workflow = OCRWorkflow(
            extractor=PDFExtractor(),
            ocr=ocr_backend,
            storage=None,
        )

        self._build_ui()
        self._connect_signals()
        self._update_templates_combo()
        app_signals.templates_changed.connect(self._update_templates_combo)
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("OCR")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

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

        # ---- Выбор файла ----
        self.input_edit = QLineEdit()
        self.input_button = QPushButton("Browse")
        menu = QMenu(self)
        menu.addAction("PDF File", self._browse_file)
        menu.addAction("Folder", self._browse_folder)
        self.input_button.setMenu(menu)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)
        right_panel.addLayout(input_layout)
        right_panel.addSpacing(10)

        # ---- ocr buttons ----
        ocr_row = QHBoxLayout()
        self.ocr_button = QPushButton("Распознать выделенную область")
        self.ocr_button.setMinimumHeight(40)
        self.ocr_button.setEnabled(False)
        ocr_row.addWidget(self.ocr_button, 4)

        self.auto_ocr_checkbox = QCheckBox("Auto")
        self.auto_ocr_checkbox.setChecked(False)
        ocr_row.addWidget(self.auto_ocr_checkbox, 1)

        right_panel.addLayout(ocr_row)

        self.clear_button = QPushButton("Отменить выделение")
        self.clear_button.setMinimumHeight(40)
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
        self.clear_button.clicked.connect(self._undo_selection)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        self.viewer.lock_toggled.connect(self._on_lock_toggled)     
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
        if not directory:
            return

        try:
            normalizer = DirectoryNormalizer(directory)
            normalizer.normalize_structure()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка нормализации", str(e))
            return

        orig_path = Path(directory)
        normalized_path = orig_path.with_name(orig_path.name + "_hardlink")
        if not normalized_path.exists():
            normalized_path = orig_path

        self.session.input_mode = "folder"
        self.session.queue = [str(p) for p in self.queue_service.get_pending(normalized_path)]
        if not self.session.queue:
            QMessageBox.information(self, "Информация", "Все PDF уже распознаны.")
            return

        self.session.current_index = 0
        self.input_edit.blockSignals(True)
        self.input_edit.setText(str(normalized_path))
        self.input_edit.blockSignals(False)
        self._load_pdf(self.session.queue[0])
                
    def _finish_folder_processing(self):
        from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QPlainTextEdit, QHBoxLayout

        folder_path = self.input_edit.text().strip()
        if not folder_path or not Path(folder_path).exists():
            self._reset_state()
            QMessageBox.information(self, "Готово", "Все PDF обработаны")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Предпросмотр структуры")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        label = QLabel("Будет создана следующая структура папок:")
        layout.addWidget(label)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        try:
            tree = preview_structure(Path(folder_path))
            text_edit.setPlainText(tree)
        except Exception as e:
            text_edit.setPlainText(f"Ошибка получения структуры: {str(e)}")

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Структуризировать")
        cancel_btn = QPushButton("Пропустить")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        result = dialog.exec()

        if result == QDialog.Accepted:
            try:
                res = structure_pdfs(Path(folder_path))
                if "error" in res:
                    QMessageBox.critical(self, "Ошибка структуризации", res["error"])
                else:
                    QMessageBox.information(
                        self,
                        "Структуризация завершена",
                        f"Перемещено файлов: {res['moved']}\nОшибок: {res['errors']}"
                    )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
        else:
            QMessageBox.information(self, "Пропущено", "Структуризация не выполнена.")

        self._reset_state()
        QMessageBox.information(self, "Готово", "Все PDF обработаны")            
            
    def _update_templates_combo(self):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("Не использовать", -1)
        templates = get_templates()
        for idx, tpl in enumerate(templates):
            # Показываем name, если есть, иначе pattern
            display = tpl.get("name", tpl.get("pattern", f"Шаблон {idx+1}"))
            self.template_combo.addItem(display, idx)
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

    def _load_pdf(self, pdf_path):
        if not pdf_path:
            return

        self.session.pdf_path = pdf_path
        self.session.zones = []
        self.session.zone_texts = []
        self.session.zone_ids = [] 

        self.viewer.load_pdf(pdf_path, 0)

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
        self._update_view_rects()
        self.result_text.setPlainText(f"PDF загружен:\n{pdf_path}")

        if self.session.locked and self.session.locked_rects:
            self.session.zones.clear()
            self.session.zone_texts.clear()
            self.session.zone_ids.clear()
            current_page = self.viewer.current_page() + 1 
            for r in self.session.locked_rects:
                new_region = Region(
                    page=current_page,
                    x=r.x,
                    y=r.y,
                    w=r.w,
                    h=r.h
                )
                self.session.zones.append(new_region)
            self._update_view_rects()
            self.ocr_info.setText(f"Выделено областей: {len(self.session.zones)}")
            self._run_ocr()

    def _on_path_changed(self, path: str):
        if not path.strip():
            return

        p = Path(path)

        if p.is_file():
            self.session.input_mode = "file"
            self.session.queue = []
            self.session.current_index = -1
            self._load_pdf(str(p))
            return

        if p.is_dir():
            self.session.input_mode = "folder"
            self.session.queue = [str(p) for p in self.queue_service.get_pending(p)]
            if self.session.queue:
                self.session.current_index = 0
                self._load_pdf(self.session.queue[0])
            else:
                self.result_text.setPlainText("Все PDF уже распознаны.")
                self.session.queue = []
                self.session.current_index = -1

    def _change_page(self, page_num: int):
        if hasattr(self, '_changing_page') and self._changing_page:
            return
        self._changing_page = True
        try:
            self.viewer.go_to_page(page_num - 1)
            total_pages = self.page_spin.maximum()
            self.prev_btn.setEnabled(page_num > 1)
            self.next_btn.setEnabled(page_num < total_pages)
            self.page_info.setText(f"Страница {page_num} из {total_pages}")
            self._update_view_rects()
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

    # ---------- от зависаний ----------
    def _set_ocr_running(self, running):
        self._ocr_running = running
        self.ocr_button.setEnabled(not running and bool(self.session.zones))
        self.apply_btn.setEnabled(not running)

    def _on_ocr_finished(self, results):
        self._set_ocr_running(False)

        if results is None:
            return

        self.session.zone_texts = [r.text for r in results]
        self.session.zone_ids = [r.storage_id for r in results]

        self.result_text.clear()
        for idx, r in enumerate(results):
            self.result_text.appendPlainText(f"{{zone{idx}}} {r.text}")

        self.ocr_info.setText(f"Выделено областей: {len(results)}")

    def _on_ocr_error(self, message):
        self._set_ocr_running(False)
        QMessageBox.critical(self, "Ошибка OCR", message)

    def _cleanup_ocr_worker(self):
        if self._ocr_worker is not None:
            self._ocr_worker.deleteLater()
            self._ocr_worker = None
        if self._ocr_thread is not None:
            self._ocr_thread.deleteLater()
            self._ocr_thread = None


    # ---------- Выделение областей ----------
    def _on_rect_selected(self, region: Region):
        self.session.zones.append(region)
        count = len(self.session.zones)
        self.ocr_info.setText(f"Выделено областей: {count}")
        self.ocr_button.setEnabled(count > 0)
        zone_index = count - 1
        self.result_text.appendPlainText(f"zone{zone_index}: {region}")
        self._update_view_rects()
        if self.auto_ocr_checkbox.isChecked():
            self._run_ocr()

    def _undo_selection(self):
        if not self.session.zones:
            return
        self.viewer.remove_last_rect()
        self.session.zones.pop()
        if self.session.zone_texts:
            self.session.zone_texts.pop()
        if self.session.zone_ids:
            self.session.zone_ids.pop()
        count = len(self.session.zones)
        self.ocr_info.setText(f"Выделено областей: {count}")
        self.ocr_button.setEnabled(count > 0)
        self._refresh_result_text()
        self._update_view_rects()
        
    def _on_lock_toggled(self, locked):
        self.session.locked = locked
        if locked:
            self.session.locked_rects = self.session.zones.copy()
        else:
            self.session.locked_rects = []
            self._clear_selection()

    def _update_view_rects(self):
        if not hasattr(self, 'viewer') or not self.viewer:
            return
        current_page = self.viewer.current_page()
        dpi = self.viewer.get_dpi()
        scale = dpi / 72.0 
        filtered = [
            (r.x * scale, r.y * scale, r.w * scale, r.h * scale)
            for r in self.session.zones
            if r.page == current_page + 1
        ]
        self.viewer.set_rects(filtered)

    def _refresh_result_text(self):
        self.result_text.clear()
        for idx, region in enumerate(self.session.zones):
            self.result_text.appendPlainText(f"zone{idx}: {region}")

    def _clear_selection(self):
        self.viewer.clear_selection()
        self.session.zones.clear()
        self.session.zone_texts.clear()
        self.session.zone_ids.clear()
        self.ocr_info.setText("Выделено областей: 0")
        self.ocr_button.setEnabled(False)
        self._update_view_rects()
        
    # ---------- Основной OCR ----------
    def _run_ocr(self):
        if self._ocr_running:
            return

        if not self.session.pdf_path or not self.session.zones:
            QMessageBox.warning(self, "Ошибка", "Не выбран PDF или не выделена область.")
            return

        config = load_config()
        self.ocr_workflow.ensure_storage(
            enabled=config.get("ocr_storage_enabled", False),
            storage_path=Path("ocr_storage")
        )

        try:
            self.ocr_workflow.ocr.reload_from_config()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Ошибка OCR", str(e))
            return

        self._ocr_thread = QThread(self)
        self._ocr_worker = OCRWorker(
            self.ocr_workflow,
            self.session.pdf_path,
            self.session.zones,
            dpi=300
        )
        self._ocr_worker.moveToThread(self._ocr_thread)

        self._ocr_thread.started.connect(self._ocr_worker.run)
        self._ocr_worker.finished.connect(self._on_ocr_finished)
        self._ocr_worker.error.connect(self._on_ocr_error)
        self._ocr_worker.finished.connect(self._ocr_thread.quit)
        self._ocr_worker.error.connect(self._ocr_thread.quit)
        self._ocr_thread.finished.connect(self._cleanup_ocr_worker)

        self._set_ocr_running(True)
        self._ocr_thread.start()
        
    def _apply_action(self):
        if not self.session.pdf_path:
            return

        if hasattr(self.viewer, 'close_document'):
            self.viewer.close_document()
        else:
            try:
                self.viewer.load_pdf(None)
            except:
                pass

        old_file = Path(self.session.pdf_path)

        # --- 1. Парсинг исправлений из поля результата ---
        current_text = self.result_text.toPlainText()
        lines = current_text.splitlines()
        import re
        pattern_zone = re.compile(r'\{zone(\d+)\}\s*(.*)')
        updates = {}
        for line in lines:
            match = pattern_zone.match(line)
            if match:
                idx = int(match.group(1))
                txt = match.group(2)
                updates[idx] = txt

        for idx, new_txt in updates.items():
            if 0 <= idx < len(self.session.zone_texts):
                if new_txt != self.session.zone_texts[idx]:
                    self.session.zone_texts[idx] = new_txt
                    if self.ocr_workflow.storage is not None:
                        self.ocr_workflow.update_zone_text(self.session.zone_ids[idx], new_txt)

        # --- 2. Получение шаблона ---
        selected_idx = get_selected_template_index()
        pattern = None
        structure_pattern = None
        if selected_idx >= 0:
            templates = get_templates()
            if selected_idx < len(templates):
                tpl = templates[selected_idx]
                pattern = tpl.get("pattern")
                structure_pattern = tpl.get("structure")
            else:
                set_selected_template_index(-1)

        # --- 3. Переименование и обновление manifest через сервис ---
        try:
            new_file = self.file_workflow.apply_rename(
                pdf_path=old_file,
                zone_texts=self.session.zone_texts,
                template_pattern=pattern,
                manual_name=self.filename_edit.text().strip()
            )
            self.session.pdf_path = str(new_file)

            self.file_workflow.update_manifest(
                old_path=old_file,
                new_path=new_file,
                template_pattern=pattern,
                zone_texts=self.session.zone_texts,
                structure_pattern=structure_pattern   # новое
            )
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать файл:\n{e}")
            return

        # --- 4. Переход к следующему PDF (если папка) ---
        if self.session.input_mode == "folder":
            self.session.current_index += 1
            if self.session.current_index < len(self.session.queue):
                next_pdf = self.session.queue[self.session.current_index]
                self._load_pdf(next_pdf)
            else:
                self._finish_folder_processing()

    def _reset_state(self):
        # Создаём новую сессию
        self.session = OCRSession()
        
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

        self.ocr_info.setText("Выделено областей: 0")

        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)

        self.page_info.setText("Страница 1 из 1")

        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        self.ocr_button.setEnabled(False)