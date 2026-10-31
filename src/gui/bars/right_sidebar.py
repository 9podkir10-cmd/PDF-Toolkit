import os

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QStackedWidget, QTabBar, QVBoxLayout, QWidget

from gui.panels.index import IndexToolsPanel
from gui.panels.read import ReadToolsPanel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "assets", "icons"))
ICON_INDEX = os.path.join(ICON_DIR, "sidebar/index.svg")
ICON_READ = os.path.join(ICON_DIR, "sidebar/read.svg")

class RightSidebar(QWidget):
    # Сигнал, сообщающий MainWindow, что вкладка переключилась (0 = Read, 1 = Index)
    tab_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightSidebar")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Вкладки (Mode Tabs)
        self.tabs = QTabBar()
        self.tabs.setObjectName("toolsTabBar")
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setIconSize(QSize(16, 16))
        
        self.tabs.addTab("Read")
        self.tabs.addTab("Index")
        self.tabs.setTabIcon(0, QIcon(ICON_READ))
        self.tabs.setTabIcon(1, QIcon(ICON_INDEX))
        
        layout.addWidget(self.tabs)

        # 2. Контент панелей
        self.stack = QStackedWidget()
        
        self.read_panel = ReadToolsPanel()
        self.index_panel = IndexToolsPanel()
        
        self.stack.addWidget(self.read_panel)
        self.stack.addWidget(self.index_panel)
        
        layout.addWidget(self.stack, 1)

        # Связываем переключение вкладки с переключением контента
        self.tabs.currentChanged.connect(self.stack.setCurrentIndex)
        # И сообщаем наверх, что режим изменился
        self.tabs.currentChanged.connect(self.tab_changed.emit)