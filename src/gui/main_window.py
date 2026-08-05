from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from .sidebar import Sidebar
from .pages import (
    DashboardPage,
    SplitPage,
    ExportPage,
    IndexPage,
    PatchPage,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF-Toolkit")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(220)

        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.split_page = SplitPage()
        self.export_page = ExportPage()
        self.index_page = IndexPage()
        self.patch_page = PatchPage()

        self.stack.addWidget(self.dashboard_page)   # index 0
        self.stack.addWidget(self.split_page)       # index 1
        self.stack.addWidget(self.export_page)      # index 2
        self.stack.addWidget(self.index_page)       # index 3
        self.stack.addWidget(self.patch_page)       # index 4

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        self.sidebar.dashboard_clicked.connect(
            lambda: self.stack.setCurrentIndex(0)
        )

        self.sidebar.split_clicked.connect(
            lambda: self.stack.setCurrentIndex(1)
        )

        self.sidebar.export_clicked.connect(
            lambda: self.stack.setCurrentIndex(2)
        )

        self.sidebar.index_clicked.connect(
            lambda: self.stack.setCurrentIndex(3)
        )

        self.sidebar.patch_clicked.connect(
            lambda: self.stack.setCurrentIndex(4)
        )