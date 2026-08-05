import os
from pathlib import Path
from backend.barcodes import (
    process_single_pdf_file,
    process_directory,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QFileDialog,
    QComboBox,
    QMessageBox,
    QMenu
)


class PatchPage(QWidget):
    def __init__(self):
        super().__init__()

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("Split by Barcode")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        description = QLabel(
            "Split PDF documents using barcode separators."
        )
        description.setWordWrap(True)
        main_layout.addWidget(description)

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
            "patch1",
            "patch2",
            "patch3",
            "patch4",
            "patchT",
        ])

        form.addRow("Barcode:", self.mode_box)

        main_layout.addLayout(form)


        self.run_button = QPushButton("Process PDF")
        self.run_button.setMinimumHeight(40)

        main_layout.addWidget(self.run_button)

        main_layout.addStretch()

    def _connect_signals(self):
        self.output_button.clicked.connect(self._browse_output)
        self.run_button.clicked.connect(self._run)

    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
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

    def _run(self):
        input_path = self.input_edit.text().strip()
        output_dir = self.output_edit.text().strip() or None
        mode = self.mode_box.currentText()

        if not input_path:
            QMessageBox.warning(
                self,
                "Missing Input",
                "Please select a PDF file or folder."
            )
            return

        if not os.path.exists(input_path):
            QMessageBox.critical(
                self,
                "Error",
                f"Path does not exist:\n{input_path}"
            )
            return

        try:
            #
            # Single PDF
            #
            if os.path.isfile(input_path):

                if not input_path.lower().endswith(".pdf"):
                    QMessageBox.warning(
                        self,
                        "Invalid File",
                        "Please select a PDF file."
                    )
                    return

                created_files = process_single_pdf_file(
                    input_path,
                    [mode],
                    output_dir,
                )

                if created_files:
                    QMessageBox.information(
                        self,
                        "Completed",
                        f"Created {len(created_files)} file(s)."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Completed",
                        f"Barcode '{mode}' was not found."
                    )

            #
            # Directory
            #
            elif os.path.isdir(input_path):

                result = process_directory(
                    input_path,
                    [mode],
                    output_dir,
                )

                processed = 0
                created = 0

                for files in result["results"].values():
                    if files:
                        processed += 1
                        created += len(files)

                QMessageBox.information(
                    self,
                    "Completed",
                    f"Processed PDFs: {processed}\n"
                    f"Created files: {created}"
                )

            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Input must be a PDF file or a folder."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Patch Error",
                str(e)
            )