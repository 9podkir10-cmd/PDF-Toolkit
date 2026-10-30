from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from gui.widgets.viewer_for_read import ReadViewer 

class ViewerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_path = ""
        self._build_ui()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Основной контент
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        main_layout.addLayout(content_layout, 1)

        # Левая панель - PDF Viewer For Read
        left_panel = QVBoxLayout()
        self.viewer = ReadViewer()
        left_panel.addWidget(self.viewer)
        content_layout.addLayout(left_panel, 4)

        # Правая панель (для будущих инструментов)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        right_panel.addSpacing(10)

        # ---- Заголовок "Инструменты" ----
        # ---- поиск ctrl f ----
        # ---- заметка ctrl n ----
        # ---- маркер ctrl m ----
        # ---- подчеркивание ----
        # ---- стрелка ----
        # ---- ластик ----
        
        # Заглушка, чтобы панель не схлопывалась
        right_panel.addWidget(QLabel("Инструменты в разработке..."))
        right_panel.addStretch()

        content_layout.addLayout(right_panel, 2)
        main_layout.addStretch()

    # --- Методы для интеграции с MainWindow (TitleBar) ---
    def open_file(self, file_path: str):
        self.current_path = file_path
        self.viewer.load_pdf(file_path)

    def open_folder(self, folder_path: str):
        # Если нужно поведение при открытии папки — реализуем позже
        self.current_path = folder_path
        pass