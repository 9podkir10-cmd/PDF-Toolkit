import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .bars.right_sidebar import RightSidebar
from .bars.secondary_sidebar import SecondarySidebar
from .bars.sidebar import Sidebar
from .bars.title_bar import CustomTitleBar
from .pages import (
    DashboardPage,
    ExportPage,
    ScanPage,
    SettingsPage,
    SplitPage,
    ViewerPage,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.current_path = ""
        self._left_sidebar_width = 250
        self._right_sidebar_width = 340      
        self._pages_with_sidebar = {0, 1, 2}
        self._build_ui()
        self._connect_signals()
        self._update_sidebar_visibility(self.stack.currentIndex())

    def _connect_signals(self):
        self.title_bar.open_file_requested.connect(self._open_file_dialog)
        self.title_bar.open_folder_requested.connect(self._open_folder_dialog)
        self.title_bar.path_submitted.connect(self._handle_global_path)
        self.secondary_sidebar.file_double_clicked.connect(self._handle_global_path)
        # self.index_page.path_changed.connect(self._update_ui_path)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(64)
        bottom_layout.addWidget(self.sidebar)

        self.secondary_sidebar = SecondarySidebar()
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainContent")
        self.stack.setMinimumWidth(500) 

        self.viewer_page = ViewerPage()
        self.split_page = SplitPage()
        self.export_page = ExportPage()
        self.scan_page = ScanPage()
        self.dashboard_page = DashboardPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.viewer_page)      # 0
        self.stack.addWidget(self.export_page)      # 1
        self.stack.addWidget(self.split_page)       # 2
        self.stack.addWidget(self.scan_page)        # 3
        self.stack.addWidget(self.dashboard_page)   # 4
        self.stack.addWidget(self.settings_page)    # 5
        
        self.right_sidebar = RightSidebar()
        self.viewer_page.bind_tools_panel(self.right_sidebar.index_panel)
        self.right_sidebar.tab_changed.connect(self.viewer_page.set_mode)

        
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 1. Левый второй сайдбар (Explorer)
        self.splitter.addWidget(self.secondary_sidebar)
        
        # 2. Основной контент
        self.splitter.addWidget(self.stack)       
        
        # 3. Правый сайдбар (Tools)
        self.splitter.addWidget(self.right_sidebar)        

        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(2, True)
        self.splitter.setHandleWidth(1)
        
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        
        self.splitter.setSizes([self._left_sidebar_width, 9999, self._right_sidebar_width])
        
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        bottom_layout.addWidget(self.splitter, 1)
        main_layout.addWidget(bottom_widget, 1)

        self.sidebar.viewer_clicked.connect(lambda: self._switch_page(0))
        self.sidebar.export_clicked.connect(lambda: self._switch_page(1))
        self.sidebar.split_clicked.connect(lambda: self._switch_page(2))
        self.sidebar.scan_clicked.connect(lambda: self._switch_page(3))
        self.sidebar.dashboard_clicked.connect(lambda: self._switch_page(4))
        self.sidebar.settings_clicked.connect(lambda: self._switch_page(5))

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*.*)")
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

    def _on_splitter_moved(self, _, index: int):
        sizes = self.splitter.sizes()
        if index == 1: self._left_sidebar_width = sizes[0]
        elif index == 2: self._right_sidebar_width = sizes[2]
                
    def _update_sidebar_visibility(self, index: int):
        needs_sidebar = index in self._pages_with_sidebar
        
        if needs_sidebar:
            self.secondary_sidebar.show()
            self.right_sidebar.show()
            self.splitter.setHandleWidth(1)
            self.splitter.setSizes([self._left_sidebar_width, 9999, self._right_sidebar_width])
        else:
            self.secondary_sidebar.hide()
            self.right_sidebar.hide()
            self.splitter.setHandleWidth(0)   
            self.splitter.setSizes([0, 9999, 0])

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