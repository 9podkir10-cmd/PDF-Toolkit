from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QSizePolicy,
)


class Sidebar(QWidget):
    dashboard_clicked = Signal()
    split_clicked = Signal()
    export_clicked = Signal()
    index_clicked = Signal()
    ocr_clicked = Signal()
    patch_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("sidebar")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(10)

        title = QLabel("PDF-Toolkit")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
        """)

        layout.addWidget(title)
        layout.addSpacing(20)

        self.dashboard_button = QPushButton("Dashboard")
        self.split_button = QPushButton("Split PDF")
        self.export_button = QPushButton("Export")
        self.index_button = QPushButton("Index")
        self.ocr_button = QPushButton("OCR")
        self.patch_button = QPushButton("Patch")
        self.settings_button = QPushButton("Settings")

        buttons = [
            (self.dashboard_button, self.dashboard_clicked),
            (self.split_button, self.split_clicked),
            (self.export_button, self.export_clicked),
            (self.index_button, self.index_clicked),
            (self.ocr_button, self.ocr_clicked),
            (self.patch_button, self.patch_clicked),
        ]

        for button, signal in buttons:
            button.setMinimumHeight(40)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            layout.addWidget(button)
            button.clicked.connect(signal.emit)

        layout.addStretch()
        
        self.settings_button.setMinimumHeight(40)
        self.settings_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(self.settings_button)
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        