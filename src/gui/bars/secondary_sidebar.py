import os

from PySide6.QtCore import QDir, Qt, Signal
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from backend.explorer import ExplorerWidget


class FileExplorerWidget(QWidget):
    """Внутренний виджет для отображения дерева файлов."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileExplorer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- ЗАГОЛОВОК EXPLORER ---
        header_widget = QWidget()
        header_widget.setObjectName("explorerHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        self.title_label = QLabel("Explorer")
        self.title_label.setObjectName("explorerTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        main_layout.addWidget(header_widget)
        # --------------------------

        # Стек для переключения между пустым состоянием и деревом
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 1. Заглушка (когда папка не выбрана)
        self.empty_label = QLabel("No folder opened")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666666; font-size: 12px;")
        self.stacked_widget.addWidget(self.empty_label)

        # 2. Само дерево
        self.tree = QTreeView()
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self.tree.setModel(self.model)
        
        # Настройки внешнего вида
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(12) # Чуть уменьшили отступ для компактности
        self.tree.setRootIsDecorated(True)
        self.tree.setExpandsOnDoubleClick(True)
        
        for i in range(1, self.model.columnCount()):
            self.tree.setColumnHidden(i, True)

        self.stacked_widget.addWidget(self.tree)
        self.stacked_widget.setCurrentWidget(self.empty_label)

    def set_root_path(self, path: str):
        if not path or not os.path.exists(path):
            self.stacked_widget.setCurrentWidget(self.empty_label)
            return

        if os.path.isfile(path):
            path = os.path.dirname(path)

        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.stacked_widget.setCurrentWidget(self.tree)


class SecondarySidebar(QStackedWidget):
    file_double_clicked = Signal(str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("secondarySidebar")
        self.preferred_width = 250 
        self.setMaximumWidth(400)
        self.explorers = [] 
        self._build_pages()

    def _build_pages(self):
        for _ in range(4):
            explorer = ExplorerWidget()
            explorer.file_double_clicked.connect(self.file_double_clicked.emit)
            self.addWidget(explorer)
            self.explorers.append(explorer)


        for _ in range(3):
            self.addWidget(QWidget())

    def set_root_path(self, path: str):
        for explorer in self.explorers:
            explorer.set_root_path(path)

    def set_active(self, active: bool):
        if active:
            self.setMinimumWidth(180)
            self.setMaximumWidth(400)
            self.show()
        else:
            self.setMinimumWidth(0)
            self.setMaximumWidth(0)
            self.show()