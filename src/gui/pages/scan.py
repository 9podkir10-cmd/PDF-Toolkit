import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox,
    QFileDialog, QProgressBar
)

from backend.scan_b import ScannerBackend, list_scan_profiles


class ScanWorker(QObject):
    log_signal = Signal(str)
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(self, scanner_name: str, profile_name: str, output_folder: str,
                 base_filename: str, split_by_barcode: bool, barcode_modes: list):
        super().__init__()
        self.scanner_name = scanner_name
        self.profile_name = profile_name
        self.output_folder = output_folder
        self.base_filename = base_filename
        self.split_by_barcode = split_by_barcode
        self.barcode_modes = barcode_modes

    def run(self):
        try:
            backend = ScannerBackend(self.profile_name)
            self.log_signal.emit(f"Подключение к сканеру {self.scanner_name}...")
            if not backend.open_device_by_name(self.scanner_name):
                self.error_signal.emit("Не удалось подключиться к сканеру.")
                return
            self.log_signal.emit("Начинаем сканирование...")
            result_files = backend.scan_to_pdf(
                output_folder=self.output_folder,
                base_filename=self.base_filename,
                split_by_barcode=self.split_by_barcode,
                barcode_modes=self.barcode_modes
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

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("Scan")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(15)

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Без профиля", None)
        form.addRow("Профиль:", self.profile_combo)

        scanner_layout = QHBoxLayout()
        self.scanner_label = QLabel("Не выбран")
        self.scanner_label.setMinimumWidth(200)
        self.select_scanner_btn = QPushButton("Выбрать сканер...")
        scanner_layout.addWidget(self.scanner_label)
        scanner_layout.addWidget(self.select_scanner_btn)
        form.addRow("Сканер:", scanner_layout)

        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Папка для сохранения")
        self.browse_output_btn = QPushButton("Обзор...")
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.browse_output_btn)
        form.addRow("Папка вывода:", output_layout)

        self.filename_edit = QLineEdit("scan")
        form.addRow("Имя файла (без расширения):", self.filename_edit)

        self.split_check = QCheckBox("Разделить по штрих-кодам")
        self.split_check.setChecked(False)
        form.addRow("", self.split_check)

        modes_label = QLabel("Режимы штрих-кодов:")
        modes_label.setEnabled(False)
        self.modes_list = QListWidget()
        self.modes_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.modes_list.setMaximumHeight(80)
        self.modes_list.setEnabled(False)
        for mode in ["patch1", "patch2", "patch3", "patch4", "patchT"]:
            item = QListWidgetItem(mode)
            item.setSelected(True)
            self.modes_list.addItem(item)

        modes_layout = QVBoxLayout()
        modes_layout.addWidget(modes_label)
        modes_layout.addWidget(self.modes_list)
        form.addRow("", modes_layout)

        main_layout.addLayout(form)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.scan_btn = QPushButton("Сканировать")
        self.scan_btn.setMinimumHeight(40)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.scan_btn)
        main_layout.addLayout(progress_layout)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.log_text.setPlaceholderText("Лог сканирования...")
        main_layout.addWidget(self.log_text)

        main_layout.addStretch()

    def _connect_signals(self):
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self.select_scanner_btn.clicked.connect(self._select_scanner)
        self.browse_output_btn.clicked.connect(self._browse_output)
        self.scan_btn.clicked.connect(self._start_scan)
        self.split_check.stateChanged.connect(self._toggle_modes)

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
            backend = ScannerBackend()
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

    def _toggle_modes(self, state):
        enabled = state == Qt.Checked
        self.modes_list.setEnabled(enabled)
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QFormLayout):
                for row in range(item.rowCount()):
                    label = item.itemAt(row, QFormLayout.LabelRole)
                    field = item.itemAt(row, QFormLayout.FieldRole)
                    if field and field.widget() == self.modes_list:
                        if label and label.widget():
                            label.widget().setEnabled(enabled)
                        break

    def _get_selected_modes(self) -> list:
        if not self.split_check.isChecked():
            return []
        selected = []
        for item in self.modes_list.selectedItems():
            selected.append(item.text())
        return selected

    def _start_scan(self):
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
        split = self.split_check.isChecked()
        modes = self._get_selected_modes()
        scanner_name = self.scanner_backend.get_selected_scanner_name()

        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.clear()
        self.log_text.appendPlainText("Инициализация...")

        self.thread = QThread()
        self.worker = ScanWorker(
            scanner_name=scanner_name,
            profile_name=profile_name,
            output_folder=output_folder,
            base_filename=base_filename,
            split_by_barcode=split,
            barcode_modes=modes
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