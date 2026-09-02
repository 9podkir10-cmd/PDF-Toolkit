import os
import shutil
import tempfile
from typing import Optional

from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QSpinBox, QGroupBox
)

from backend.scan_b import ScannerBackend, list_scan_profiles
from backend.scanning.folder_scanner import FolderScanner
from backend.scanning.batch_manager import BatchManager
from backend.scanning.models import Page
from gui.widgets.thumbnail_viewer import BatchPreviewWidget


class ScanWorker(QObject):
    log_signal = Signal(str)
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(self, scanner_name: str, profile_name: str, output_folder: str,
                 base_filename: str, split_by_barcode: bool, barcode_modes: list,
                 split_by_count: Optional[int] = None,
                 use_mock: bool = False):
        super().__init__()
        self.scanner_name = scanner_name
        self.profile_name = profile_name
        self.output_folder = output_folder
        self.base_filename = base_filename
        self.split_by_barcode = split_by_barcode
        self.barcode_modes = barcode_modes
        self.split_by_count = split_by_count
        self.use_mock = use_mock

    def run(self):
        try:
            backend = ScannerBackend(self.profile_name, use_mock=self.use_mock)
            self.log_signal.emit(f"Подключение к сканеру {self.scanner_name}...")
            if not backend.open_device_by_name(self.scanner_name):
                self.error_signal.emit("Не удалось подключиться к сканеру.")
                return
            self.log_signal.emit("Начинаем сканирование...")
            result_files = backend.scan_to_pdf(
                output_folder=self.output_folder,
                base_filename=self.base_filename,
                split_by_barcode=self.split_by_barcode,
                barcode_modes=self.barcode_modes,
                split_by_count=self.split_by_count
            )
            backend.cleanup_temp()
            if result_files:
                self.log_signal.emit(f"Создано файлов: {len(result_files)}")
                self.finished_signal.emit(result_files)
            else:
                self.log_signal.emit("Сканирование не дало результатов.")
                self.finished_signal.emit([])
        except Exception as e:
            self.error_signal.emit(str(e))


class ScanPage(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.thread = None
        self.scanner_backend = None
        self._build_ui()
        self._connect_signals()
        self._load_profiles()
        self._update_split_options()
        self._toggle_mock_mode(Qt.Unchecked)

    def _build_ui(self):
        # Главный горизонтальный макет
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # ----- Левая панель (1/4) с настройками -----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Scan")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        left_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Без профиля", None)
        form.addRow("Профиль:", self.profile_combo)

        scanner_layout = QHBoxLayout()
        self.scanner_label = QLabel("Не выбран")
        self.scanner_label.setMinimumWidth(200)
        self.select_scanner_btn = QPushButton("Выбрать...")
        scanner_layout.addWidget(self.scanner_label)
        scanner_layout.addWidget(self.select_scanner_btn)
        form.addRow("Сканер:", scanner_layout)

        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Папка для сохранения")
        self.browse_output_btn = QPushButton("Обзор")
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.browse_output_btn)
        form.addRow("Папка вывода:", output_layout)

        self.filename_edit = QLineEdit("scan")
        form.addRow("Имя файла (без расшир.):", self.filename_edit)

        self.mock_check = QCheckBox("Тестовый режим (без сканера)")
        self.mock_check.setChecked(False)
        form.addRow("", self.mock_check)

        self.load_folder_btn = QPushButton("Загрузить папку с изображениями")
        self.load_folder_btn.setEnabled(False)
        form.addRow("", self.load_folder_btn)

        self.split_mode_combo = QComboBox()
        self.split_mode_combo.addItems([
            "Без разделения",
            "По штрих-кодам",
            "По количеству страниц"
        ])
        form.addRow("Разделение:", self.split_mode_combo)

        left_layout.addLayout(form)

        self.barcode_group = QGroupBox("Параметры штрих-кодов")
        barcode_layout = QVBoxLayout(self.barcode_group)
        modes_label = QLabel("Режимы штрих-кодов:")
        self.modes_list = QListWidget()
        self.modes_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.modes_list.setMaximumHeight(80)
        for mode in ["patch1", "patch2", "patch3", "patch4", "patchT"]:
            item = QListWidgetItem(mode)
            item.setSelected(True)
            self.modes_list.addItem(item)
        barcode_layout.addWidget(modes_label)
        barcode_layout.addWidget(self.modes_list)
        left_layout.addWidget(self.barcode_group)

        self.count_group = QGroupBox("Разделение по количеству")
        count_layout = QHBoxLayout(self.count_group)
        count_layout.addWidget(QLabel("Страниц на документ:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 999)
        self.count_spin.setValue(2)
        count_layout.addWidget(self.count_spin)
        count_layout.addStretch()
        left_layout.addWidget(self.count_group)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.scan_btn = QPushButton("Сканировать")
        self.scan_btn.setMinimumHeight(35)
        self.export_btn = QPushButton("Экспортировать Batch в PDF")
        self.export_btn.setEnabled(False)
        self.export_btn.setMinimumHeight(35)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.scan_btn)
        progress_layout.addWidget(self.export_btn)
        left_layout.addLayout(progress_layout)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setPlaceholderText("Лог сканирования...")
        left_layout.addWidget(self.log_text)

        left_layout.addStretch()

        # ----- Правая панель (3/4) с предпросмотром -----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(5)

        self.preview_widget = BatchPreviewWidget()
        self.preview_widget.setVisible(False)
        right_layout.addWidget(self.preview_widget)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)

    def _connect_signals(self):
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self.select_scanner_btn.clicked.connect(self._select_scanner)
        self.browse_output_btn.clicked.connect(self._browse_output)
        self.scan_btn.clicked.connect(self._start_scan)
        self.export_btn.clicked.connect(self._export_batch)
        self.split_mode_combo.currentIndexChanged.connect(self._update_split_options)
        self.mock_check.stateChanged.connect(self._toggle_mock_mode)
        self.load_folder_btn.clicked.connect(self._load_images_from_folder)

    def _load_profiles(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Без профиля", None)
        profiles = list_scan_profiles()
        for name in profiles:
            self.profile_combo.addItem(name, name)
        self.profile_combo.blockSignals(False)

    def _profile_changed(self, index):
        pass

    def _select_scanner(self):
        try:
            use_mock = self.mock_check.isChecked()
            backend = ScannerBackend(use_mock=use_mock)
            if backend.select_scanner_interactive():
                self.scanner_backend = backend
                self.scanner_label.setText(backend.get_selected_scanner_name())
                self.log_text.appendPlainText(f"Выбран сканер: {backend.get_selected_scanner_name()}")
            else:
                self.scanner_label.setText("Не выбран")
                self.log_text.appendPlainText("Выбор сканера отменён.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            self.scanner_label.setText("Ошибка")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self.output_edit.setText(folder)

    def _toggle_mock_mode(self, state):
        enabled = state == Qt.Checked
        self.load_folder_btn.setEnabled(enabled)
        if not enabled:
            self.preview_widget.setVisible(False)

            self.export_btn.setEnabled(False)
            if self.scanner_backend and self.scanner_backend.use_mock:
                self.scanner_backend = None
                self.scanner_label.setText("Не выбран")
        else:
            self.preview_widget.setVisible(True)
            self.preview_widget.batch_label.setText("Batch: Не загружен")

    def _update_split_options(self):
        mode = self.split_mode_combo.currentText()
        if mode == "По штрих-кодам":
            self.barcode_group.setVisible(True)
            self.count_group.setVisible(False)
        elif mode == "По количеству страниц":
            self.barcode_group.setVisible(False)
            self.count_group.setVisible(True)
        else:
            self.barcode_group.setVisible(False)
            self.count_group.setVisible(False)

    def _get_selected_modes(self) -> list:
        selected = []
        for item in self.modes_list.selectedItems():
            selected.append(item.text())
        return selected

    def _load_images_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if not folder:
            return

        try:
            scanner = FolderScanner(folder)
            scanner.open(folder)
            scanned_pages = list(scanner.acquire())
            scanner.close()

            if not scanned_pages:
                QMessageBox.warning(self, "Ошибка", "В папке нет поддерживаемых изображений.")
                return

            pages = [Page(image=sp.image, page_number=sp.page_number) for sp in scanned_pages]

            mode = self.split_mode_combo.currentText()
            split_by_count = None
            if mode == "По количеству страниц":
                split_by_count = self.count_spin.value()

            batch = BatchManager.create_batch_from_pages(pages, split_by_count)

            self.preview_widget.display_batch(batch)
            self.preview_widget.setVisible(True)
            self.export_btn.setEnabled(True)

            self.log_text.appendPlainText(
                f"Загружено {len(pages)} страниц, создано {len(batch.documents)} документов."
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображения: {e}")

    def _export_batch(self):
        """Экспортирует текущий Batch в PDF-файлы."""
        batch = self.preview_widget.get_batch()
        if not batch or not batch.documents:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта. Сначала загрузите Batch.")
            return

        output_folder = self.output_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения.")
            return
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку: {e}")
                return

        base_filename = self.filename_edit.text().strip() or "scan"

        try:
            total_docs = len(batch.documents)
            for idx, doc in enumerate(batch.documents, start=1):
                images = [page.image for page in doc.pages]
                if not images:
                    continue

                temp_dir = tempfile.mkdtemp()
                temp_pdf_path = os.path.join(temp_dir, "temp.pdf")
                images[0].save(
                    temp_pdf_path,
                    save_all=True,
                    append_images=images[1:],
                    format="PDF",
                    resolution=100.0
                )

                dest_name = f"{base_filename}_doc{idx:02d}.pdf"
                dest_path = os.path.join(output_folder, dest_name)
                shutil.copy(temp_pdf_path, dest_path)

                shutil.rmtree(temp_dir, ignore_errors=True)

                self.log_text.appendPlainText(f"Создан: {dest_path}")

            self.log_text.appendPlainText(f"Экспорт завершён. Создано {total_docs} PDF-файлов.")
            QMessageBox.information(self, "Готово", f"Все {total_docs} документов экспортированы в PDF.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")

    def _start_scan(self):
        if self.mock_check.isChecked():
            self._load_images_from_folder()
            return

        if not self.scanner_backend or not self.scanner_backend.get_selected_scanner_name():
            QMessageBox.warning(self, "Ошибка", "Сначала выберите сканер.")
            return

        output_folder = self.output_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения.")
            return
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку: {e}")
                return

        base_filename = self.filename_edit.text().strip()
        if not base_filename:
            base_filename = "scan"

        profile_name = self.profile_combo.currentData()
        scanner_name = self.scanner_backend.get_selected_scanner_name()
        use_mock = self.mock_check.isChecked()

        mode = self.split_mode_combo.currentText()
        split_by_barcode = False
        split_by_count = None
        barcode_modes = []

        if mode == "По штрих-кодам":
            split_by_barcode = True
            barcode_modes = self._get_selected_modes()
            if not barcode_modes:
                QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один режим штрих-кода.")
                return
        elif mode == "По количеству страниц":
            split_by_count = self.count_spin.value()

        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.clear()
        self.log_text.appendPlainText("Инициализация...")

        self.thread = QThread()
        self.worker = ScanWorker(
            scanner_name=scanner_name,
            profile_name=profile_name,
            output_folder=output_folder,
            base_filename=base_filename,
            split_by_barcode=split_by_barcode,
            barcode_modes=barcode_modes,
            split_by_count=split_by_count,
            use_mock=use_mock
        )
        self.worker.moveToThread(self.thread)

        self.worker.log_signal.connect(self._on_log)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_log(self, message: str):
        self.log_text.appendPlainText(message)

    def _on_finished(self, files: list):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        # Включаем кнопку экспорта, но проверка на наличие данных будет в _export_batch
        self.export_btn.setEnabled(True)
        if files:
            self.log_text.appendPlainText(f"Готово. Создано файлов: {len(files)}")
            for f in files:
                self.log_text.appendPlainText(f"  {f}")
        else:
            self.log_text.appendPlainText("Ничего не создано.")
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.worker.deleteLater()

    def _on_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.log_text.appendPlainText(f"Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка сканирования", error_msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.worker.deleteLater()

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        event.accept()