import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QWidget,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "assets", "icons", "title_bar"))
MAIN_ICON = "src/assets/icon.ico"
ICON_MINIMIZE = os.path.join(ICON_DIR, "Minimize.svg")
ICON_MAXIMIZE = os.path.join(ICON_DIR, "Maximize.svg")
ICON_RESTORE  = os.path.join(ICON_DIR, "Restore.svg")
ICON_CLOSE    = os.path.join(ICON_DIR, "Close.svg")

class CustomTitleBar(QWidget):
    open_file_requested = Signal()
    open_folder_requested = Signal()
    path_submitted = Signal(str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self.setObjectName("customTitleBar")
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        # лого
        self.icon_label = QLabel()
        self.title_label = QLabel("PDF-Toolkit")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addSpacing(15)

        # файл
        self.btn_file = QPushButton("File")
        self.file_menu = QMenu(self)
        self.file_menu.addAction("Open File", self.open_file_requested.emit)
        self.file_menu.addAction("Open Folder", self.open_folder_requested.emit)
        self.btn_file.setMenu(self.file_menu)
        layout.addWidget(self.btn_file)
        
        layout.addStretch(1) 

        # путь
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("pathEdit")
        self.path_edit.setPlaceholderText("No file or folder selected...")
        self.path_edit.setMinimumWidth(400)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        self.path_edit.editingFinished.connect(self._on_path_entered)
        layout.addWidget(self.path_edit)

        layout.addStretch(1)

        self.btn_minimize = QPushButton()
        self.btn_minimize.setObjectName("btnMinimize")
        self.btn_minimize.setFlat(True)
        self.btn_minimize.setIcon(QIcon(ICON_MINIMIZE))
        self.btn_minimize.setIconSize(QSize(14, 14))
        self.btn_minimize.clicked.connect(self._minimize)

        self.btn_maximize = QPushButton()
        self.btn_maximize.setObjectName("btnMaximize")
        self.btn_maximize.setFlat(True)  
        self.btn_maximize.setIcon(QIcon(ICON_RESTORE))
        self.btn_maximize.setIconSize(QSize(14, 14))
        self.btn_maximize.clicked.connect(self._maximize_restore)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("btnClose")
        self.btn_close.setFlat(True)     
        self.btn_close.setIcon(QIcon(ICON_CLOSE))
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.clicked.connect(self._close)

        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

        self.setFixedHeight(32) 

    def _minimize(self):
        self.parent_window.showMinimized()

    def _maximize_restore(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            if os.path.exists(ICON_MAXIMIZE):
                self.btn_maximize.setIcon(QIcon(ICON_MAXIMIZE))
        else:
            self.parent_window.showMaximized()
            self.btn_maximize.setIcon(QIcon(ICON_RESTORE))

    def _close(self):
        self.parent_window.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                if os.path.exists(ICON_MAXIMIZE):
                    self.btn_maximize.setIcon(QIcon(ICON_MAXIMIZE))
                else:
                    self.btn_maximize.setIcon(QIcon(ICON_RESTORE))
                
                self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
                
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._maximize_restore()
            event.accept()
            
    def _on_path_entered(self):
        path = self.path_edit.text().strip()
        if path and path != self.parent_window.current_path:
            self.path_submitted.emit(path)

    def set_path(self, path: str):
        self.path_edit.setText(path)