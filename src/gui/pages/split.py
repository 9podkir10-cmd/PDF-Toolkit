import os
from backend.extract_pages import (
    extract_pages,
    process_all_pdfs,
)
from backend.barcodes import (
    process_single_pdf_file,
    process_directory,
    find_pdf_files,
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QMenu,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QMessageBox,
)


class SplitWorker(QObject):
    log_signal = Signal(str)
    finished = Signal()
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, input_path, output_path, mode, value, start, end, patch_codes=None):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode
        self.value = value
        self.start = start
        self.end = end
        self.patch_codes = patch_codes if patch_codes is not None else []

    def run(self):
        try:
            if self.mode == "patch":
                if os.path.isfile(self.input_path):
                    self.log_signal.emit(f"Processing single PDF: {self.input_path}")
                    created = process_single_pdf_file(
                        self.input_path,
                        self.patch_codes,
                        self.output_path or None
                    )
                    self.log_signal.emit(f"Created files: {len(created)}")
                    self.progress.emit(100)
                elif os.path.isdir(self.input_path):
                    pdf_files = find_pdf_files(self.input_path)
                    total = len(pdf_files)
                    if total == 0:
                        self.log_signal.emit("No PDF files found.")
                        self.progress.emit(100)
                        self.finished.emit()
                        return
                    self.log_signal.emit(f"Found {total} PDF files.")
                    total_created = 0
                    for i, pdf_file in enumerate(pdf_files, 1):
                        progress_val = int((i / total) * 100)
                        self.progress.emit(progress_val)
                        self.log_signal.emit(f"Processing {i}/{total}: {os.path.basename(pdf_file)}")
                        created = process_single_pdf_file(
                            pdf_file,
                            self.patch_codes,
                            self.output_path or None
                        )
                        total_created += len(created)
                    self.progress.emit(100)
                    self.log_signal.emit(f"Total created files: {total_created}")
                else:
                    self.error.emit("Input must be a PDF file or a folder.")
                    return
            else:
                if os.path.isfile(self.input_path):
                    self.log_signal.emit(f"Processing single PDF: {self.input_path}")
                    extract_pages(
                        self.input_path,
                        self.output_path or None,
                        self.mode,
                        self.value,
                        self.start,
                        self.end,
                        log_callback=lambda msg: self.log_signal.emit(msg)
                    )
                    self.progress.emit(100)
                elif os.path.isdir(self.input_path):
                    pdf_files = find_pdf_files(self.input_path)
                    total = len(pdf_files)
                    if total == 0:
                        self.log_signal.emit("No PDF files found.")
                        self.progress.emit(100)
                        self.finished.emit()
                        return
                    self.log_signal.emit(f"Found {total} PDF files.")
                    for i, pdf_file in enumerate(pdf_files, 1):
                        progress_val = int((i / total) * 100)
                        self.progress.emit(progress_val)
                        self.log_signal.emit(f"Processing {i}/{total}: {os.path.basename(pdf_file)}")
                        extract_pages(
                            pdf_file,
                            self.output_path or None,
                            self.mode,
                            self.value,
                            self.start,
                            self.end,
                            log_callback=lambda msg: self.log_signal.emit(msg)
                        )
                    self.progress.emit(100)
                    self.log_signal.emit("All files processed.")
                else:
                    self.error.emit("Input must be a PDF file or a folder.")
                    return
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class SplitPage(QWidget):
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("Split PDF")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(15)

        self.input_edit = QLineEdit()
        self.input_button = QPushButton("Browse")
        menu = QMenu(self)
        menu.addAction("PDF File", self._browse_file)
        menu.addAction("Folder", self._browse_folder)
        self.input_button.setMenu(menu)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)
        form.addRow("Input:", input_layout)

        self.output_edit = QLineEdit()
        self.output_button = QPushButton("Browse")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.output_button)
        form.addRow("Output:", output_layout)

        self.mode_box = QComboBox()
        self.mode_box.addItems(["first", "last", "range", "patch"])
        form.addRow("Mode:", self.mode_box)

        self.value_spin = QSpinBox()
        self.value_spin.setMinimum(1)
        self.value_spin.setMaximum(9999)
        form.addRow("Pages:", self.value_spin)

        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(1)
        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(1)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Start"))
        range_layout.addWidget(self.start_spin)
        range_layout.addSpacing(20)
        range_layout.addWidget(QLabel("End"))
        range_layout.addWidget(self.end_spin)

        self.range_group = QGroupBox("Page Range")
        self.range_group.setLayout(range_layout)

        main_layout.addLayout(form)
        main_layout.addWidget(self.range_group)

        self.patch_combo = QComboBox()
        self.patch_combo.addItems(["patch1", "patch2", "patch3", "patch4", "patchT"])
        patch_layout = QVBoxLayout()
        patch_layout.addWidget(QLabel("Select a barcode:"))
        patch_layout.addWidget(self.patch_combo)
        self.patch_group = QGroupBox("Page Patch")
        self.patch_group.setLayout(patch_layout)
        self.patch_group.setEnabled(False)

        main_layout.addWidget(self.patch_group)

        self.run_button = QPushButton("Split")
        self.run_button.setMinimumHeight(40)
        main_layout.addWidget(self.run_button)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(320)
        self.log_text.setPlaceholderText("Processing log...")
        main_layout.addWidget(self.log_text)

        main_layout.addStretch()
        self._update_mode()

    def _connect_signals(self):
        self.output_button.clicked.connect(self._browse_output)
        self.mode_box.currentIndexChanged.connect(self._update_mode)
        self.run_button.clicked.connect(self._run)

    def _log(self, message: str):
        self.log_text.appendPlainText(message)

    def _log_progress(self, value: int):
        self._log(f"Progress: {value}%")

    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )
        if filename:
            self.input_edit.setText(filename)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.input_edit.setText(directory)

    def _browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if directory:
            self.output_edit.setText(directory)

    def _update_mode(self):
        mode = self.mode_box.currentText()
        if mode == "range":
            self.value_spin.setEnabled(False)
            self.range_group.setEnabled(True)
            self.patch_group.setEnabled(False)
        elif mode == "patch":
            self.value_spin.setEnabled(False)
            self.range_group.setEnabled(False)
            self.patch_group.setEnabled(True)
        else:
            self.value_spin.setEnabled(True)
            self.range_group.setEnabled(False)
            self.patch_group.setEnabled(False)

    def _run(self):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "Busy", "Processing is already running.")
            return

        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()
        mode = self.mode_box.currentText()
        value = self.value_spin.value()
        start = self.start_spin.value()
        end = self.end_spin.value()

        if not input_path:
            QMessageBox.warning(self, "Input Required", "Please select a PDF file or folder.")
            return

        if mode in ("first", "last") and value <= 0:
            QMessageBox.warning(self, "Invalid Value", "Number of pages must be greater than 0.")
            return

        if mode == "range":
            if start <= 0 or end <= 0:
                QMessageBox.warning(self, "Invalid Range", "Page numbers must be greater than 0.")
                return
            if start > end:
                QMessageBox.warning(self, "Invalid Range", "Start page cannot be greater than end page.")
                return

        patch_codes = [self.patch_combo.currentText()] if mode == "patch" else None

        self.run_button.setEnabled(False)

        self.worker = SplitWorker(
            input_path, output_path, mode, value, start, end, patch_codes
        )
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        self.worker.log_signal.connect(self._log)
        self.worker.progress.connect(self._log_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def _on_finished(self):
        self._cleanup_thread()
        self._log("Progress: 100%")
        QMessageBox.information(self, "Finished", "Processing completed successfully.")

    def _on_error(self, error_msg):
        self._cleanup_thread()
        self._log(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)

    def _cleanup_thread(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None
        self.run_button.setEnabled(True)