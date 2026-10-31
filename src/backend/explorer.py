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


class ExplorerWidget(QWidget):
    file_double_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileExplorer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setObjectName("explorerHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        self.title_label = QLabel("Explorer")
        self.title_label.setObjectName("explorerTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        main_layout.addWidget(header_widget)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 1. Заглушка
        self.empty_label = QLabel("No folder opened")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666666; font-size: 12px;")
        self.stacked_widget.addWidget(self.empty_label)

        # 2. Дерево
        self.tree = QTreeView()
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(12)
        
        for i in range(1, self.model.columnCount()):
            self.tree.setColumnHidden(i, True)

        self.tree.doubleClicked.connect(self._on_double_click)

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

    def _on_double_click(self, index):
        path = self.model.filePath(index)
        
        if os.path.isfile(path):
            self.file_double_clicked.emit(path)