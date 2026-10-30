import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QMainWindow, QStackedWidget, QWidget, QSplitter, QFileDialog)
from .bars.sidebar import Sidebar
from .bars.title_bar import CustomTitleBar
from .bars.secondary_sidebar import SecondarySidebar
from .pages import (DashboardPage, SplitPage, ExportPage, Ocr_fPage, ScanPage, ViewerPage, SettingsPage)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_path = ""
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._sidebar_width = 250
        self._page_needs_sidebar = {
            0: True,   # Viewer
            1: True,   # Export
            2: True,   # Index
            3: True,   # Split
            4: False,  # Scan
            5: False,  # Dashboard
            6: False,  # Settings
        }
        self._build_ui()
        self._connect_signals()
        self._update_sidebar_visibility(self.stack.currentIndex())

    def _connect_signals(self):
        self.title_bar.open_file_requested.connect(self._open_file_dialog)
        self.title_bar.open_folder_requested.connect(self._open_folder_dialog)
        self.title_bar.path_submitted.connect(self._handle_global_path)
        self.secondary_sidebar.file_double_clicked.connect(self._handle_global_path)
        self.index_page.path_changed.connect(self._update_ui_path)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # 1. Главный вертикальный слой (TitleBar сверху, всё остальное снизу)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # 2. Нижняя часть интерфейса (Сайдбар + Контент)
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # Первый сайдбар с иконками
        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(64)
        bottom_layout.addWidget(self.sidebar)

        # Второй сайдбар контейнер
        self.secondary_sidebar = SecondarySidebar()

        self.stack = QStackedWidget()
        self.stack.setObjectName("mainContent") 

        self.viewer_page = ViewerPage()
        self.split_page = SplitPage()
        self.export_page = ExportPage()
        self.index_page = Ocr_fPage()
        self.scan_page = ScanPage()
        self.dashboard_page = DashboardPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.viewer_page)      # index 0
        self.stack.addWidget(self.export_page)      # index 1
        self.stack.addWidget(self.index_page)       # index 2
        self.stack.addWidget(self.split_page)       # index 3
        self.stack.addWidget(self.scan_page)        # index 4
        self.stack.addWidget(self.dashboard_page)   # index 5
        self.stack.addWidget(self.settings_page)    # index 6

        # Заглушки 
        self.secondary_sidebar.addWidget(QWidget()) # 0: Для Viewer
        self.secondary_sidebar.addWidget(QWidget()) # 1: Для Export
        self.secondary_sidebar.addWidget(QWidget()) # 2: Для Index
        self.secondary_sidebar.addWidget(QWidget()) # 3: Для Split
        self.secondary_sidebar.addWidget(QWidget()) # 4: Для Scan
        self.secondary_sidebar.addWidget(QWidget()) # 5: Для Dashboard
        self.secondary_sidebar.addWidget(QWidget()) # 6: Для Settings

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.secondary_sidebar)
        self.splitter.addWidget(self.stack)
        
        self.splitter.setCollapsible(0, True)
        self.splitter.setHandleWidth(1)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([self._sidebar_width, 800]) 
        
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        bottom_layout.addWidget(self.splitter, 1)
        main_layout.addWidget(bottom_widget, 1)

        self.sidebar.viewer_clicked.connect(lambda: self._switch_page(0))
        self.sidebar.export_clicked.connect(lambda: self._switch_page(1))
        self.sidebar.index_clicked.connect(lambda: self._switch_page(2))
        self.sidebar.split_clicked.connect(lambda: self._switch_page(3))
        self.sidebar.scan_clicked.connect(lambda: self._switch_page(4))
        self.sidebar.dashboard_clicked.connect(lambda: self._switch_page(5))
        self.sidebar.settings_clicked.connect(lambda: self._switch_page(6))

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*.*)"
        )
        if file_path:
            self._handle_global_path(file_path)

    def _open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder_path:
            self._handle_global_path(folder_path)

    def _handle_global_path(self, path: str):
        self.current_path = path
        self.title_bar.set_path(path)
        self.secondary_sidebar.set_root_path(path)
        current_page = self.stack.currentWidget()
        
        if os.path.isfile(path):
            if hasattr(current_page, "open_file"):
                current_page.open_file(path)
        elif os.path.isdir(path):
            if hasattr(current_page, "open_folder"):
                current_page.open_folder(path)

    def _on_splitter_moved(self, pos: int, index: int):
        if index == 1:
            sizes = self.splitter.sizes()
            if sizes[0] > 10:
                self._sidebar_width = sizes[0]

    def _update_sidebar_visibility(self, index: int):
        needs_sidebar = self._page_needs_sidebar.get(index, False)
        handle = self.splitter.handle(1)
        
        if needs_sidebar:
            self.secondary_sidebar.show()
            self.splitter.setHandleWidth(1)
            self.splitter.setSizes([self._sidebar_width, max(self.splitter.width() - self._sidebar_width, 100)])
        else:
            self.splitter.setHandleWidth(1)
            if handle:
                handle.setEnabled(False) 
                handle.setCursor(Qt.ArrowCursor)
            self.splitter.setSizes([0, self.splitter.width()])

    def _update_ui_path(self, path: str):
        self.current_path = path
        self.title_bar.set_path(path)
        self.secondary_sidebar.set_root_path(path)

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.secondary_sidebar.setCurrentIndex(index)
        self._update_sidebar_visibility(index)
        
        if self.current_path:
            self._handle_global_path(self.current_path)