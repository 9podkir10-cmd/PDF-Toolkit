from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QPlainTextEdit, QComboBox,
    QTabWidget, QLabel, QPushButton, QScrollArea, QMenu, QCheckBox, QSpinBox, QFileDialog
)

from gui.widgets.pdf_viewer import BasePDFGraphicsView

class ViewerPage(QWidget):
    def __init__(self):
        super().__init__()
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
        self.viewer = BasePDFGraphicsView()
        left_panel.addWidget(self.viewer)
        content_layout.addLayout(left_panel, 4)





        # Правая панель
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)


        right_panel.addSpacing(10)

        # ---- Заголовок "Инструменты" ----
        # ---- поиск ctrl f ----
        # ---- заметка ctrl n ----
        # ---- маркер ctrl m ----
        # ---- подчеркивание "Инструменты" ----
        # ---- стрелка "Инструменты" ----
        # ---- ластик "Инструменты" ----
        # ---- Заголовок "Инструменты" ----
        # ---- Заголовок "Инструменты" ----
        # ---- Заголовок "Инструменты" ----
        # ---- Заголовок "Инструменты" ----
 
 
 
 
 
 
        right_panel.addSpacing(15)



        content_layout.addLayout(right_panel, 2)

        main_layout.addStretch()
        
        
        
        
    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if filename:
            self.input_edit.setText(filename)

    def _browse_folder(self):
        pass