import os
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QPushButton, QVBoxLayout, QWidget, QLabel, QSizePolicy)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "assets", "icons", "sidebar"))
ICON_DASHBOARD = os.path.join(ICON_DIR, "dashboard.svg")
ICON_EXPORT    = os.path.join(ICON_DIR, "export.svg")
ICON_INDEX     = os.path.join(ICON_DIR, "index.svg")
ICON_SPLIT     = os.path.join(ICON_DIR, "split.svg")
ICON_SCAN      = os.path.join(ICON_DIR, "scan.svg")
ICON_VIEWER    = os.path.join(ICON_DIR, "viewer.svg")
ICON_SETTINGS  = os.path.join(ICON_DIR, "settings.svg")


class Sidebar(QWidget):
    viewer_clicked = Signal()
    export_clicked = Signal()
    index_clicked = Signal()
    split_clicked = Signal()
    scan_clicked = Signal()
    settings_clicked = Signal()
    dashboard_clicked = Signal()

    def __init__(self):
        super().__init__()
        self._all_buttons = []
        self.setObjectName("sidebar")
        self._build_ui()
        self._update_active_state(self.viewer_button)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 20, 8, 20) 
        layout.setSpacing(10)

        self.viewer_button = QPushButton()
        self.export_button = QPushButton()
        self.index_button = QPushButton()
        self.split_button = QPushButton()
        self.scan_button = QPushButton()
        self.dashboard_button = QPushButton()
        self.settings_button = QPushButton()

        buttons = [
            (self.viewer_button, self.viewer_clicked, ICON_VIEWER, "PDF/TXT Viewer"),            
            (self.export_button, self.export_clicked, ICON_EXPORT, "Export"),
            (self.index_button, self.index_clicked, ICON_INDEX, "Index"),
            (self.split_button, self.split_clicked, ICON_SPLIT, "Split"),        
            (self.scan_button, self.scan_clicked, ICON_SCAN, "Scan"),
        ]

        for button, signal, icon_path, tooltip in buttons:
            self._setup_button(button, signal, icon_path, tooltip)
            layout.addWidget(button)

        layout.addStretch()
        
        bottom_buttons = [
            (self.dashboard_button, self.dashboard_clicked, ICON_DASHBOARD, "Dashboard"),
            (self.settings_button, self.settings_clicked, ICON_SETTINGS, "Settings"),
        ]
        
        for button, signal, icon_path, tooltip in bottom_buttons:
            self._setup_button(button, signal, icon_path, tooltip)
            layout.addWidget(button)

    def _setup_button(self, button, signal, icon_path, tooltip):
        button.setMinimumHeight(48)
        button.setFixedSize(48,48)
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(24, 24))
        button.setToolTip(tooltip)
        self._all_buttons.append(button)
        button.clicked.connect(signal.emit)
        button.clicked.connect(lambda checked=False, b=button: self._update_active_state(b))

    def _update_active_state(self, clicked_button):
        for btn in self._all_buttons:
            is_active = (btn == clicked_button)

            btn.setProperty("active", "true" if is_active else "false")

            btn.style().unpolish(btn)
            btn.style().polish(btn)