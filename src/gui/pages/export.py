from pathlib import Path
from backend.collect_data import scan_and_export
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QMenu,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QMessageBox,
    QHBoxLayout,
    QFormLayout,
    QFileDialog,
    QComboBox,
    QListWidget,
    QListWidgetItem,
)


class ExportPage(QWidget):
    def __init__(self):
        super().__init__()

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title = QLabel("Export Metadata")
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


        self.format_box = QComboBox()
        self.format_box.addItems([
            "excel",
            "csv",
            "json",
            "parquet",
            "html",
            "markdown",
            "text",
            "tsv",
            "clipboard",
        ])

        form.addRow("Format:", self.format_box)

        main_layout.addLayout(form)


        columns_label = QLabel("Columns")

        self.columns_list = QListWidget()
        self.columns_list.setFixedHeight(310)

        columns = [
            "id",
            "file_name",
            "parent_directory",
            "file_path",
            "file_size",
            "date_created",
            "date_modified",
            "pages",
            "file_extension",
            "file_name_hyperlink",
        ]

        for column in columns:
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.columns_list.addItem(item)

        main_layout.addWidget(columns_label)
        main_layout.addWidget(self.columns_list)


        self.run_button = QPushButton("Export")
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

    def _selected_columns(self):
        columns = []

        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)

            if item.checkState() == Qt.Checked:
                columns.append(item.text())

        return columns

    def _run(self):
        input_path = self.input_edit.text().strip()

        if not input_path:
            QMessageBox.warning(
                self,
                "Missing Input",
                "Please select a PDF file or directory."
            )
            return

        input_path = Path(input_path)

        if not input_path.exists():
            QMessageBox.critical(
                self,
                "Error",
                f"Path does not exist:\n{input_path}"
            )
            return

        columns = self._selected_columns()

        export_format = self.format_box.currentText()


        if export_format == "clipboard":
            output_path = None
        else:
            output = self.output_edit.text().strip()

            output_path = output if output else None

        try:
            scan_and_export(
                input_path=str(input_path),
                output_path=output_path,
                format=export_format,
                columns=columns,
)

            QMessageBox.information(
                self,
                "Export Complete",
                "Metadata exported successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                str(e)
            )