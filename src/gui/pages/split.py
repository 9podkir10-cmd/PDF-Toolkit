import os
from backend.extract_pages import (
    extract_pages,
    process_all_pdfs,
)
from backend.barcodes import (
    process_single_pdf_file,
    process_directory,
)
from PySide6.QtCore import Qt, Signal
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


class SplitPage(QWidget):
    log = Signal(str)
    def __init__(self):
        super().__init__()

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

        self.input_button = QPushButton("Browse ▼")
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
        self.mode_box.addItems([
            "first",
            "last",
            "range",
            "patch"       
        ])

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

        # ---- Page Patch ----
        self.patch_combo = QComboBox()
        self.patch_combo.addItems([
            "patch1",
            "patch2",
            "patch3",
            "patch4",
            "patchT"
        ])

        patch_layout = QVBoxLayout()
        patch_layout.addWidget(QLabel("Выберите штрихкод:"))
        patch_layout.addWidget(self.patch_combo)

        self.patch_group = QGroupBox("Page Patch")
        self.patch_group.setLayout(patch_layout)
        self.patch_group.setEnabled(False)

        main_layout.addWidget(self.range_group)
        main_layout.addWidget(self.patch_group)

        self.run_button = QPushButton("Run Split")
        self.run_button.setMinimumHeight(40)

        main_layout.addWidget(self.run_button)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Processing log...")

        main_layout.addWidget(self.log)


        main_layout.addStretch()


        self._update_mode()

    def _connect_signals(self):
        self.output_button.clicked.connect(self._browse_output)

        self.mode_box.currentIndexChanged.connect(self._update_mode)

        self.run_button.clicked.connect(self._run)

    def _log(self, message: str):
        self.log.appendPlainText(message)

    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if filename:
            self.input_edit.setText(filename)


    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Folder"
        )

        if directory:
            self.input_edit.setText(directory)

    def _browse_output(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder"
        )

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
        else:  # first, last
            self.value_spin.setEnabled(True)
            self.range_group.setEnabled(False)
            self.patch_group.setEnabled(False)

    def _run(self):
        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()

        mode = self.mode_box.currentText()
        value = self.value_spin.value()
        start = self.start_spin.value()
        end = self.end_spin.value()

        if not input_path:
            QMessageBox.warning(
                self,
                "Input Required",
                "Please select a PDF file or folder."
            )
            return

        if mode in ("first", "last") and value <= 0:
            QMessageBox.warning(
                self,
                "Invalid Value",
                "Number of pages must be greater than 0."
            )
            return

        if mode == "range":
            if start <= 0 or end <= 0:
                QMessageBox.warning(
                    self,
                    "Invalid Range",
                    "Page numbers must be greater than 0."
                )
                return

            if start > end:
                QMessageBox.warning(
                    self,
                    "Invalid Range",
                    "Start page cannot be greater than end page."
                )
                return

        try:
            if mode == "patch":
                if os.path.isfile(input_path):
                    if not input_path.lower().endswith(".pdf"):
                        QMessageBox.warning(self, "Invalid File", "Please select a PDF file.")
                        return
                    created = process_single_pdf_file(
                        input_path,
                        [self.patch_combo.currentText()],
                        output_path or None
                    )
                    self._log(f"Создано файлов: {len(created)}")
                elif os.path.isdir(input_path):
                    result = process_directory(
                        input_path,
                        [self.patch_combo.currentText()],
                        output_path or None
                    )
                    total_created = 0
                    for files in result["results"].values():
                        total_created += len(files)
                    self._log(f"Обработано PDF: {len(result['results'])}\nСоздано файлов: {total_created}")
                else:
                    QMessageBox.critical(self, "Error", "Input must be a PDF file or a folder.")
                    return

                QMessageBox.information(self, "Finished", "Splitting by barcode completed successfully.")
            else:
                if os.path.isdir(input_path):
                    process_all_pdfs(
                        input_path,
                        output_path or None,
                        mode,
                        value,
                        start,
                        end,
                        log_callback=self._log
                    )
                else:
                    extract_pages(
                        input_path,
                        output_path or None,
                        mode,
                        value,
                        start,
                        end,
                        log_callback=self._log
                    )
                QMessageBox.information(self, "Finished", "PDF splitting completed successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

            QMessageBox.information(
                self,
                "Finished",
                "PDF splitting completed successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )