from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ReadToolsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("readToolsPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Инструменты чтения"))
        
        # Заглушки для будущих функций
        self.btn_search = QPushButton("Поиск (Ctrl+F)")
        self.btn_marker = QPushButton("Маркер")
        self.btn_underline = QPushButton("Подчеркивание")
        self.btn_note = QPushButton("Заметки")
        
        layout.addWidget(self.btn_search)
        layout.addWidget(self.btn_marker)
        layout.addWidget(self.btn_underline)
        layout.addWidget(self.btn_note)
        
        layout.addStretch()