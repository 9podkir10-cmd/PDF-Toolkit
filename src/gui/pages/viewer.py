import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.clear_path import DirectoryNormalizer
from backend.config import get_config_service
from backend.indexing.file_workflow import PDFFileWorkflow
from backend.indexing.models import OCRSession, RecognizedZone, Region
from backend.indexing.ocr_engine import OCREngine
from backend.indexing.queue_service import PDFQueueService
from backend.manifest import get_manifest_service
from backend.manifest.utils import find_manifest
from backend.structure import preview_structure, structure_pdfs
from gui.signals import app_signals
from gui.widgets.viewer_for_index import IndexViewer
from gui.widgets.viewer_for_read import ReadViewer


class OCRTask(QThread):
    finished = Signal(list)  # list[RecognizedZone]
    error = Signal(str)

    def __init__(self, engine: OCREngine, pdf_path: str, regions: list[Region]):
        super().__init__()
        self.engine = engine
        self.pdf_path = pdf_path
        self.regions = regions

    def run(self):
        try:
            results = self.engine.process_regions(self.pdf_path, self.regions)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ViewerPage(QWidget):
    path_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_path = ""
        self.session = OCRSession() 
        self._ocr_thread = None
        self.tools_panel = None

        self.queue_service = PDFQueueService()
        self.file_workflow = PDFFileWorkflow()
        self.config_service = get_config_service()
        self.ocr_engine = OCREngine()

        self._build_ui()
        self._connect_signals()
        app_signals.templates_changed.connect(self._update_templates_combo)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.viewer_stack = QStackedWidget()
        self.read_viewer = ReadViewer()
        self.index_viewer = IndexViewer()
        
        self.viewer_stack.addWidget(self.read_viewer)
        self.viewer_stack.addWidget(self.index_viewer)
        
        layout.addWidget(self.viewer_stack)

    def bind_tools_panel(self, panel):
        self.tools_panel = panel
        self.tools_panel.ocr_requested.connect(self._run_ocr)
        self.tools_panel.clear_requested.connect(self._undo_selection)
        self.tools_panel.apply_requested.connect(self._apply_action)
        self.tools_panel.template_changed.connect(self._on_template_changed)
        self._update_templates_combo()

    def set_mode(self, index: int):
        self.viewer_stack.setCurrentIndex(index)

    def _connect_signals(self):
        self.index_viewer.rect_selected.connect(self._on_rect_selected)
        self.index_viewer.view.page_changed.connect(self._update_view_rects)
        self.index_viewer.lock_toggled.connect(self._on_lock_toggled)     

        self.apply_shortcut = QShortcut(QKeySequence("Return"), self)
        self.apply_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.apply_shortcut.activated.connect(self._apply_action)
        
        self.apply_shortcut_numpad = QShortcut(QKeySequence("Enter"), self)
        self.apply_shortcut_numpad.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.apply_shortcut_numpad.activated.connect(self._apply_action)
        
        self.clear_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.clear_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.clear_shortcut.activated.connect(self._undo_selection)

    # ---------- Навигация и загрузка ----------
    def open_file(self, file_path: str):
        self.current_path = file_path
        self._on_path_changed(file_path)

    def open_folder(self, folder_path: str):
        if not folder_path: 
            return

        # 1. создание hardlink
        try:
            normalizer = DirectoryNormalizer(folder_path)
            normalizer.normalize_structure()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка нормализации", str(e))
            return

        orig_path = Path(folder_path)
        normalized_path = orig_path.with_name(orig_path.name + "_hardlink")
        if not normalized_path.exists(): 
            normalized_path = orig_path

        manifest_path = normalized_path / "manifest.json"
        if not manifest_path.exists():
            QMessageBox.critical(self, "Ошибка", f"Манифест не найден: {manifest_path}")
            return

        self.session.input_mode = "folder"
        self.session.manifest_path = str(manifest_path)

        # 2. Получение очереди
        pending_ids = self.queue_service.get_pending(normalized_path)
        if not pending_ids:
            QMessageBox.information(self, "Информация", "Все PDF уже распознаны или папка пуста.")
            self.session.queue_ids = []
            self.session.current_index = -1
            self.session.record_id = None
            return

        # 3. Загрузка первого файла
        self.session.queue_ids = pending_ids
        self.session.current_index = 0
        first_id = pending_ids[0]
        self.session.record_id = first_id

        service = get_manifest_service(self.session.manifest_path)
        manifest = service.load()
        if manifest is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить манифест")
            return
                
        record = service.get_record(first_id)
        if record is None:
            QMessageBox.critical(self, "Ошибка", f"Запись с ID {first_id} не найдена.")
            return

        pdf_path = normalized_path / record.filename
        if not pdf_path.exists():
            QMessageBox.critical(self, "Ошибка", f"Файл не найден: {pdf_path}")
            return

        # 4. Обновление пути в интерфейсе и загрузка PDF
        self.current_path = str(normalized_path)
        self.path_changed.emit(str(normalized_path))
        self._load_pdf(str(pdf_path))

    def _load_pdf(self, pdf_path):
        if not pdf_path: return

        self.session.pdf_path = pdf_path
        self.session.zones = []

        self.read_viewer.load_pdf(pdf_path)
        self.index_viewer.load_pdf(pdf_path)

        if self.tools_panel:
            self.tools_panel.set_zones_count(0)
            self.tools_panel.set_result_text(f"PDF загружен:\n{pdf_path}")
            self.tools_panel.set_filename(Path(pdf_path).stem)
            self.tools_panel.ocr_button.setEnabled(False)

        self._update_view_rects()

        if self.session.locked and self.session.locked_zones:
            self.session.zones.clear()
            current_page = self.index_viewer.current_page() + 1 
            for r in self.session.locked_zones:
                new_region = Region(page=current_page, x=r.x, y=r.y, w=r.w, h=r.h)
                self.session.zones.append(RecognizedZone(region=new_region))
            
            self._update_view_rects()
            if self.tools_panel:
                self.tools_panel.set_zones_count(len(self.session.zones))
            self._run_ocr()

    def _on_path_changed(self, path: str):
        if not path.strip(): return
        p = Path(path)

        if p.is_file():
            self.session.input_mode = "file"
            self.session.queue_ids = []
            self.session.current_index = -1

            manifest_path = find_manifest(p)
            record_id = None
            manifest_path_str = None

            if manifest_path:
                service = get_manifest_service(str(manifest_path))
                manifest_data = service.load()
                if manifest_data is not None:
                    for rec_id, rec in manifest_data.records.items():
                        if rec.filename == p.name:
                            record_id = rec_id
                            manifest_path_str = str(manifest_path)
                            break
                    if record_id is None and self.tools_panel:
                        self.tools_panel.set_result_text(
                            f"Запись для файла {p.name} не найдена в манифесте.\n"
                            "Переименование и обновление манифеста будут недоступны."
                        )
                elif self.tools_panel:
                    self.tools_panel.set_result_text("Не удалось загрузить манифест.")
            elif self.tools_panel:
                self.tools_panel.set_result_text("Манифест не найден. Переименование будет недоступно.")

            self.session.manifest_path = manifest_path_str
            self.session.record_id = record_id
            self._load_pdf(str(p))
            return

        if p.is_dir():
            self.open_folder(str(p))

    # ---------- Выделение областей ----------
    def _on_rect_selected(self, region: Region):
        self.session.zones.append(RecognizedZone(region=region))
        count = len(self.session.zones)
        
        if self.tools_panel:
            self.tools_panel.set_zones_count(count)
            self.tools_panel.append_result_text(f"zone{count-1}: {region}")
            
        self._update_view_rects()
        
        if self.tools_panel and self.tools_panel.is_auto_ocr_checked():
            self._run_ocr()

    def _undo_selection(self):
        if not self.session.zones: return
        self.index_viewer.remove_last_rect()
        self.session.zones.pop()
        
        if self.tools_panel:
            self.tools_panel.set_zones_count(len(self.session.zones))
        self._refresh_result_text()
        self._update_view_rects()
        
    def _on_lock_toggled(self, locked):
        self.session.locked = locked
        if locked:
            self.session.locked_zones = [z.region for z in self.session.zones]
        else:
            self.session.locked_zones = []
            self.index_viewer.setFocus()
            
    def _update_view_rects(self):
        if not hasattr(self, 'index_viewer') or not self.index_viewer: return
        current_page = self.index_viewer.current_page()
        filtered_regions = [z.region for z in self.session.zones if z.region.page == current_page + 1]
        self.index_viewer.set_rects(filtered_regions)

    def _refresh_result_text(self):
        if not self.tools_panel: return
        self.tools_panel.set_result_text("")
        for idx, zone in enumerate(self.session.zones):
            self.tools_panel.append_result_text(f"zone{idx}: {zone.region}")

    # ---------- OCR ----------
    def _run_ocr(self):
        if self._ocr_thread and self._ocr_thread.isRunning(): return
        if not self.session.pdf_path or not self.session.zones:
            QMessageBox.warning(self, "Ошибка", "Не выбран PDF или не выделена область.")
            return

        config = self.config_service.get_config()
        self.ocr_engine.enable_storage(
            enabled=config.ocr_storage_enabled, 
            storage_path=Path("ocr_storage")
        )

        regions = [z.region for z in self.session.zones]
        
        self._ocr_thread = OCRTask(self.ocr_engine, self.session.pdf_path, regions)
        self._ocr_thread.finished.connect(self._on_ocr_finished)
        self._ocr_thread.error.connect(self._on_ocr_error)
        
        if self.tools_panel:
            self.tools_panel.set_ocr_running(True)
        
        self._ocr_thread.start()

    def _on_ocr_finished(self, results: list[RecognizedZone]):
        if self.tools_panel:
            self.tools_panel.set_ocr_running(False)
            
        if not results: return

        self.session.zones = results
        
        if self.tools_panel:
            self.tools_panel.set_result_text("")
            for idx, zone in enumerate(results):
                self.tools_panel.append_result_text(f"{{zone{idx}}} {zone.text}")
            self.tools_panel.set_zones_count(len(results))

    def _on_ocr_error(self, message):
        if self.tools_panel:
            self.tools_panel.set_ocr_running(False)
        QMessageBox.critical(self, "Ошибка OCR", message)

    # ---------- Применение и шаблоны ----------
    def _update_templates_combo(self):
        self.config_service.reload()  
        templates = self.config_service.get_templates()
        selected_idx = self.config_service.get_selected_template_index()
        if self.tools_panel:
            self.tools_panel.update_templates(templates, selected_idx)

    def _on_template_changed(self, data_idx):
        self.config_service.set_selected_template_index(data_idx)

    def _apply_action(self):
        if not self.session.pdf_path or not self.tools_panel: 
            return

        # 1. Закрываем файлы перед переименованием
        if hasattr(self.read_viewer, 'close_document'):
            self.read_viewer.close_document()
        if hasattr(self.index_viewer, 'close_document'):
            self.index_viewer.close_document()

        old_file = Path(self.session.pdf_path)

        # 2. Собираем текст из поля результата и применяем исправления
        current_text = self.tools_panel.get_result_text()
        lines = current_text.splitlines()
        
        pattern_zone = re.compile(r'\{zone(\d+)\}\s*(.*)')
        updates = {}
        for line in lines:
            match = pattern_zone.match(line)
            if match:
                updates[int(match.group(1))] = match.group(2)

        for idx, new_txt in updates.items():
            if 0 <= idx < len(self.session.zones):
                if new_txt != self.session.zones[idx].text:
                    self.session.zones[idx].text = new_txt
                    if self.session.zones[idx].storage_id:
                        self.ocr_engine.update_zone_text(self.session.zones[idx].storage_id, new_txt)

        # 3. Получаем шаблон
        selected_idx = self.config_service.get_selected_template_index()
        pattern, structure_pattern = None, None
        
        if selected_idx >= 0:
            templates = self.config_service.get_templates()
            if selected_idx < len(templates):
                tpl = templates[selected_idx]
                pattern = tpl.pattern
                structure_pattern = tpl.structure
            else:
                self.config_service.set_selected_template_index(-1)

        # Подготавливаем тексты зон для переименования
        zone_texts = [z.text for z in self.session.zones]

        # 4. Переименование
        try:
            new_file = self.file_workflow.apply_rename(
                pdf_path=old_file, 
                zone_texts=zone_texts,
                template_pattern=pattern, 
                manual_name=self.tools_panel.get_filename()
            )
            self.session.pdf_path = str(new_file)
        except ValueError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать файл:\n{e}")
            return

        # 5. Обновление манифеста
        record_id = self.session.record_id
        manifest_path = self.session.manifest_path if self.session.input_mode == "folder" else find_manifest(old_file)

        if manifest_path and record_id:
            try:
                self.file_workflow.update_manifest_by_record_id(
                    record_id=record_id, manifest_path=Path(manifest_path),
                    template_pattern=pattern, zone_texts=zone_texts,
                    structure_pattern=structure_pattern, new_path=new_file,
                )
            except Exception as e:
                QMessageBox.warning(self, "Ошибка обновления манифеста", str(e))
        else:
            if manifest_path and not record_id:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Файл не найден в манифесте. Манифест не будет обновлён."
                )
            # если манифеста нет, просто пропускаем
            
        # 6. Переход к следующему файлу
        if self.session.input_mode == "folder":
            self.session.current_index += 1
            
            if self.session.current_index < len(self.session.queue_ids):
                next_id = self.session.queue_ids[self.session.current_index]
                self.session.record_id = next_id
                
                service = get_manifest_service(self.session.manifest_path)
                manifest = service.load()
                
                if manifest is None:
                    QMessageBox.critical(self, "Ошибка", "Не удалось загрузить манифест")
                    return 

                record = service.get_record(next_id)
                if record is None:
                    QMessageBox.critical(self, "Ошибка", f"Запись с ID {next_id} не найдена в манифесте")
                    return
                    
                next_pdf_path = Path(self.session.manifest_path).parent / record.filename
                self._load_pdf(str(next_pdf_path))
                
            else:
                self._finish_folder_processing()

    def _finish_folder_processing(self):
        folder_path = self.current_path.strip()
        if not folder_path or not Path(folder_path).exists():
            self._reset_state()
            QMessageBox.information(self, "Готово", "Все PDF обработаны")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Предпросмотр структуры")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Будет создана следующая структура папок:"))
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        try:
            tree = preview_structure(Path(folder_path))
            text_edit.setPlainText(tree)
        except Exception as e:
            text_edit.setPlainText(f"Ошибка получения структуры: {e!s}")

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Структуризировать")
        cancel_btn = QPushButton("Пропустить")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() == QDialog.Accepted:
            try:
                pending_ids = self.session.queue_ids
                res = structure_pdfs(Path(folder_path), pending_ids)
                if "error" in res:
                    QMessageBox.critical(self, "Ошибка структуризации", res["error"])
                else:
                    QMessageBox.information(
                        self, "Структуризация завершена",
                        f"Перемещено файлов: {res['moved']}\nОшибок: {res['errors']}"
                    )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
        else:
            QMessageBox.information(self, "Пропущено", "Структуризация не выполнена.")

        self._reset_state()
        QMessageBox.information(self, "Готово", "Все PDF обработаны")            

    def _reset_state(self):
        self.session = OCRSession()
        self.current_path = ""
        self.path_changed.emit("")

        if hasattr(self.index_viewer, "close_document"): 
            self.index_viewer.close_document()
        if hasattr(self.read_viewer, "close_document"): 
            self.read_viewer.close_document()

        self.index_viewer.clear_selection()
        
        if self.tools_panel:
            self.tools_panel.set_result_text("")
            self.tools_panel.set_zones_count(0)
            self.tools_panel.set_filename("")
            self.tools_panel.ocr_button.setEnabled(False)