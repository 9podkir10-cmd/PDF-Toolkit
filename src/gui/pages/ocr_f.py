from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QMenu, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox,
    QFileDialog, QSpinBox, QPlainTextEdit
)

from backend.ocr_b import get_pdf_path, OCRBackend
from gui.widgets.pdf_viewer import PDFViewer
from PIL import Image
import fitz
from pathlib import Path


class Ocr_fPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_pdf_path = None
        self.selected_rects = []
        self.ocr_results = []
        self.backend = OCRBackend()   
        self._build_ui()
        self._connect_signals()

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

        # Кнопки OCR
        self.ocr_button = QPushButton("Распознать выделенную область")
        self.ocr_button.setMinimumHeight(40)
        self.ocr_button.setEnabled(False)
        self.ocr_button.clicked.connect(self._run_ocr)
        right_panel.addWidget(self.ocr_button)

        self.clear_button = QPushButton("Очистить выделение")
        self.clear_button.clicked.connect(self._clear_selection)
        right_panel.addWidget(self.clear_button)


        right_panel.addSpacing(20)

        # Навигация
        right_panel.addWidget(QLabel("Навигация"))
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.page_spin.editingFinished.connect(self._on_page_edit_finished)  
        nav_layout.addWidget(self.page_spin)

        self.next_btn = QPushButton("▶")
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        right_panel.addLayout(nav_layout)

        self.page_info = QLabel("Страница 1 из 1")
        self.page_info.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(self.page_info)

        right_panel.addSpacing(15)

        # Результат OCR
        self.ocr_info = QLabel("Выделено областей: 0")
        right_panel.addWidget(self.ocr_info)
        self.result_text = QPlainTextEdit()
        self.result_text.setFixedHeight(280)
        right_panel.addWidget(self.result_text)
        
        #name
        right_panel.addWidget(QLabel("Имя файла"))

        self.filename_edit = QLineEdit()
        right_panel.addWidget(self.filename_edit)
        
        right_panel.addStretch()

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

    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf)"
        )
        if filename:
            self.input_edit.setText(filename)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.input_edit.setText(directory)
        
    def _on_page_edit_finished(self):
        page_num = self.page_spin.value()
        self._change_page(page_num)

    def _on_path_changed(self, path: str):
        if not path.strip():
            self.ocr_button.setEnabled(False)
            self.ocr_all_button.setEnabled(False)
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.page_spin.setMaximum(1)
            self.page_spin.setValue(1)
            self.page_info.setText("Страница 1 из 1")
            return

        pdf_path = get_pdf_path(path)
        if pdf_path:
            self.current_pdf_path = pdf_path
            self.viewer.load_pdf(pdf_path, 0)
            
            self.selected_rects = []
            self.ocr_results = []
            self.ocr_info.setText("Выделено областей: 0")
            self.result_text.clear()
            
            self.filename_edit.setText(Path(pdf_path).stem)
            
            total_pages = self.viewer.get_total_pages()
            
            self.page_spin.setMaximum(total_pages if total_pages > 0 else 1)
            self.page_spin.setValue(1)
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(total_pages > 1)
            self.page_info.setText(f"Страница 1 из {total_pages if total_pages > 0 else 1}")

            self.ocr_button.setEnabled(False)
            self.result_text.setPlainText(f"PDF загружен: {pdf_path}\nВыделите область на странице.")
        else:
            self.result_text.setPlainText("Ошибка: PDF не найден")

    def _change_page(self, page_num: int):
        if hasattr(self, '_changing_page') and self._changing_page:
            return
        
        self._changing_page = True
        try:
            self.viewer.go_to_page(page_num - 1)
            self.viewer.clear_selection()
            self.selected_rect = None
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

    def _on_rect_selected(self, x: int, y: int, w: int, h: int, page: int):
        new_rect = (x, y, w, h, page)
        self.selected_rects.append(new_rect)
        
        count = len(self.selected_rects)
        self.ocr_info.setText(f"Выделено областей: {count}")
        self.ocr_button.setEnabled(count > 0)
        
        self.result_text.appendPlainText(f"Добавлена область: {new_rect}")

    def _clear_selection(self):
        self.viewer.clear_selection()
        self.selected_rects = []
        self.ocr_info.setText("Выделено областей: 0")
        self.ocr_button.setEnabled(False)

    def _run_ocr(self):
        if not self.current_pdf_path or not self.selected_rects:
            QMessageBox.warning(self, "Ошибка", "Не выбрана область или файл.")
            return

        try:
            doc = fitz.open(self.current_pdf_path)
            dpi = self.viewer.dpi
            
            regions_to_process = []
            for i, (x, y, w, h, page_num) in enumerate(self.selected_rects):
                rect_pdf = fitz.Rect(
                    x / dpi * 72,
                    y / dpi * 72,
                    (x + w) / dpi * 72,
                    (y + h) / dpi * 72
                )
                regions_to_process.append({
                    'x': x, 'y': y, 'w': w, 'h': h, 
                    'page': page_num,
                    'rect_pdf': rect_pdf
                })
            doc.close()

            # === ВЫЗОВ БЭКЕНДА ===
            # Теперь processed_results - это список словарей: [{'text': '...', 'image_path': '...'}, ...]
            processed_results = self.backend.recognize(
                file_path=self.current_pdf_path, 
                regions=regions_to_process
            )
            # =====================

            self.result_text.clear()
            
            if not processed_results:
                self.result_text.appendPlainText("Результаты не получены.")
                return

            for res in processed_results:
                # 1. Выводим метаданные (координаты, страница) - формируем строку вручную
                meta_line = (
                    f"Страница {res['page']} | "
                    f"Координаты: x={res['coords']['x']}, y={res['coords']['y']}, "
                    f"w={res['coords']['w']}, h={res['coords']['h']}"
                )
                self.result_text.appendPlainText(meta_line)
                
                # Разделитель
                self.result_text.appendPlainText("-" * 40)
                
                # 2. САМОЕ ВАЖНОЕ: Берем ТОЛЬКО текст из словаря
                # res['text'] - это строка, её можно передавать в appendPlainText
                recognized_text = res.get('text', '[Текст не распознан]')
                
                if not recognized_text.strip():
                    recognized_text = "[Пустой результат]"
                    
                self.result_text.appendPlainText(recognized_text)
                
                # Опционально: можно вывести путь к сохраненной картинке для отладки
                self.result_text.appendPlainText(f"Файл сохранен: {res['image_path']}")
                self.result_text.appendPlainText("=" * 40)

            QMessageBox.information(
                self, 
                "Готово", 
                f"Обработано областей: {len(processed_results)}.\nИзображения сохранены в папке data."
            )

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "OCR Error", error_msg)
