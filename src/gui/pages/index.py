from backend.clear_path import DirectoryNormalizer
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QFileDialog,
)


class IndexPage(QWidget):
    def __init__(self):
        super().__init__()

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("Index PDF Files")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        description = QLabel(
            "Normalize the directory structure before indexing PDF files."
        )
        description.setWordWrap(True)
        main_layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(15)


        self.input_edit = QLineEdit()

        self.input_button = QPushButton("Browse")

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)

        form.addRow("Folder:", input_layout)

        main_layout.addLayout(form)

        self.run_button = QPushButton("Start Indexing")
        self.run_button.setMinimumHeight(40)

        main_layout.addWidget(self.run_button)
        main_layout.addStretch()

    def _connect_signals(self):
        self.input_button.clicked.connect(self._browse_folder)
        self.run_button.clicked.connect(self._run)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Folder"
        )

        if directory:
            self.input_edit.setText(directory)

    def _run(self):
        folder = self.input_edit.text().strip()

        if not folder:
            QMessageBox.warning(
                self,
                "Missing Folder",
                "Please select a folder."
            )
            return

        try:
            normalizer = DirectoryNormalizer(folder)
            normalizer.normalize_structure()

            QMessageBox.information(
                self,
                "Completed",
                "Directory normalization finished successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Index Error",
                str(e)
            )