import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QSpinBox, QGroupBox
)
from PIL import Image
from backend.scanning import get_scan_service, ScanRequest
from backend.scanning.models import Batch, Document, Page
from backend.config import get_config_service


class ScanWorker(QObject):
    log_signal = Signal(str)
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(
        self,
        scanner_name: Optional[str],
        output_folder: str,
        base_filename: str,
        split_by_barcode: bool,
        barcode_modes: list,
        split_by_count: Optional[int] = None,
        profile=None
    ):
        super().__init__()
        self.scanner_name = scanner_name
        self.output_folder = output_folder
        self.base_filename = base_filename
        self.split_by_barcode = split_by_barcode
        self.barcode_modes = barcode_modes
        self.split_by_count = split_by_count
        self.profile = profile

    def run(self):
        try:
            service = get_scan_service()
            self.log_signal.emit(f"Подключение к сканеру: {self.scanner_name or 'по умолчанию'}...")
            service.open_twain(self.scanner_name)
            self.log_signal.emit("Сканирование запущено (окно драйвера Avision)...")
            request = ScanRequest(
                output_folder=Path(self.output_folder),
                base_filename=self.base_filename,
                split_by_barcode=self.split_by_barcode,
                barcode_modes=self.barcode_modes,
                split_by_count=self.split_by_count,
                show_driver_ui=False,
                dpi=self.profile.dpi if self.profile else None,
                color_mode=self.profile.color_mode if self.profile else None,
                page_size=self.profile.page_size if self.profile else None,
                brightness=self.profile.brightness if self.profile else None,
                contrast=self.profile.contrast if self.profile else None,
                duplex=self.profile.duplex if self.profile else None,
            )

            result_files = service.scan(request)
            service.close()

            if result_files:
                self.log_signal.emit(f"Создано файлов: {len(result_files)}")
                self.finished_signal.emit([str(p) for p in result_files])
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
        self.config_service = get_config_service()
        self._build_ui()
        self._connect_signals()
        self._load_profiles()
        self._update_split_options()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

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
        self.browse_output_btn.setToolTip("""
Чтобы продолжить сессию явно укажите путь к сканируемой папке\n
Чтобы начать новую сессию укажите путь к родительской директории\n
1. Если сканирование осуществляется впервые - создастся папка scan\n
2. Если папка scan уже существует и вы хотите создать новую сессию\n
то укажите путь к существующей папке scan
""")
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.browse_output_btn)
        form.addRow("Папка вывода:", output_layout)

        self.split_mode_combo = QComboBox()
        self.split_mode_combo.addItems([
            "Без разделения",
            "По штрих-кодам",
            "По количеству страниц",
        ])
        form.addRow("Разделение:", self.split_mode_combo)

        left_layout.addLayout(form)

        self.barcode_group = QGroupBox("Параметры штрих-кодов")
        barcode_layout = QVBoxLayout(self.barcode_group)
        barcode_layout.addWidget(QLabel("Режимы штрих-кодов:"))
        self.modes_list = QListWidget()
        self.modes_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.modes_list.setMaximumHeight(80)
        for mode in ["patch1", "patch2", "patch3", "patch4", "patchT"]:
            item = QListWidgetItem(mode)
            item.setSelected(True)
            self.modes_list.addItem(item)
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
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.scan_btn)
        left_layout.addLayout(progress_layout)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setPlaceholderText("Лог сканирования...")
        left_layout.addWidget(self.log_text)

        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(5)

        try:
            from gui.widgets.thumbnail_viewer import BatchPreviewWidget
            self.preview_widget = BatchPreviewWidget()
            right_layout.addWidget(self.preview_widget)
        except ImportError as e:
            print(f"[ScanPage] BatchPreviewWidget не загружен: {e}")
            self.preview_widget = None

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)

    def _connect_signals(self):
        self.select_scanner_btn.clicked.connect(self._select_scanner)
        self.browse_output_btn.clicked.connect(self._browse_output)
        self.scan_btn.clicked.connect(self._start_scan)
        self.split_mode_combo.currentIndexChanged.connect(self._update_split_options)

    def _get_next_base_filename(self, output_folder: str) -> str:
        max_num = -1
        try:
            for entry in os.listdir(output_folder):
                name, _ext = os.path.splitext(entry)
                if name.isdigit():
                    max_num = max(max_num, int(name))
        except OSError:
            pass
        return str(max_num + 1)

    def _load_profiles(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Без профиля", None)
        for profile in self.config_service.get_scan_profiles():
            self.profile_combo.addItem(profile.name, profile.name)
        self.profile_combo.blockSignals(False)

    def _select_scanner(self):
        try:
            service = get_scan_service()
            devices = service.list_available_devices()
            if not devices:
                QMessageBox.warning(
                    self, "Сканеры не найдены",
                    "TWAIN-устройства не обнаружены. Проверьте подключение Avision."
                )
                return
            if len(devices) == 1:
                self.scanner_name = devices[0].name
            else:
                from PySide6.QtWidgets import QInputDialog
                names = [d.name for d in devices]
                chosen, ok = QInputDialog.getItem(
                    self, "Выбор сканера", "Устройства:", names, 0, False
                )
                if not ok:
                    return
                self.scanner_name = chosen

            self.scanner_label.setText(self.scanner_name)
            self.log_text.appendPlainText(f"Выбран сканер: {self.scanner_name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self.output_edit.setText(folder)

    def _update_split_options(self):
        mode = self.split_mode_combo.currentText()
        self.barcode_group.setVisible(mode == "По штрих-кодам")
        self.count_group.setVisible(mode == "По количеству страниц")

    def _get_selected_modes(self) -> list:
        return [item.text() for item in self.modes_list.selectedItems()]

    def _start_scan(self):
        if not getattr(self, "scanner_name", None):
            QMessageBox.warning(self, "Ошибка", "Сначала выберите сканер.")
            return

        output_folder = self.output_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения.")
            return
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку: {e}")
            return

        profile_name = self.profile_combo.currentData()
        profile = None
        if profile_name:
            for p in self.config_service.get_scan_profiles():
                if p.name == profile_name:
                    profile = p
                    break

        base_filename = self._get_next_base_filename(output_folder)

        mode = self.split_mode_combo.currentText()
        split_by_barcode = False
        split_by_count = None
        barcode_modes: list = []

        if mode == "По штрих-кодам":
            split_by_barcode = True
            barcode_modes = self._get_selected_modes()
            if not barcode_modes:
                QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один режим штрих-кода.")
                return
        elif mode == "По количеству страниц":
            split_by_count = self.count_spin.value()

        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.clear()
        self.log_text.appendPlainText("Инициализация...")

        self.thread = QThread()
        self.worker = ScanWorker(
            scanner_name=self.scanner_name,
            output_folder=output_folder,
            base_filename=base_filename,
            split_by_barcode=split_by_barcode,
            barcode_modes=barcode_modes,
            split_by_count=split_by_count,
            profile=profile,
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

    def _build_batch_from_files(self, files: list) -> Batch:
        groups: dict = {}
        for f in files:
            p = Path(f)
            groups.setdefault(str(p.parent), []).append(p)

        documents = []
        for folder in sorted(groups.keys()):
            paths = sorted(groups[folder])
            pages = []
            for idx, path in enumerate(paths, start=1):
                try:
                    img = Image.open(path)
                    img.load()
                except Exception as e:
                    print(f"[ScanPage] не удалось открыть {path}: {e}")
                    continue
                pages.append(Page(page_number=idx, image=img))
            if not pages:
                continue
            doc_name = Path(folder).name or "Документ"
            documents.append(Document(name=doc_name, pages=pages))

        batch_name = Path(files[0]).parent.parent.name if files else "scan"
        return Batch(name=batch_name, documents=documents)

    def _show_preview(self, files: list):
        if self.preview_widget is None or not files:
            return
        try:
            batch = self._build_batch_from_files(files)
            self.preview_widget.display_batch(batch)
            self.preview_widget.setVisible(True)
        except Exception as e:
            print(f"[ScanPage] ошибка предпросмотра: {e}")

    def _on_finished(self, files: list):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        if files:
            self.log_text.appendPlainText(f"Готово. Создано файлов: {len(files)}")
            for f in files:
                self.log_text.appendPlainText(f"  {f}")
            self._show_preview(files)
        else:
            self.log_text.appendPlainText("Ничего не создано.")
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if self.worker:
            self.worker.deleteLater()

    def _on_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.log_text.appendPlainText(f"Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка сканирования", error_msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if self.worker:
            self.worker.deleteLater()

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        event.accept()