from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QLineEdit
from .pdf_viewer import BasePDFViewer, BasePDFGraphicsView

class ReadingGraphicsView(BasePDFGraphicsView):
    """Специфичный View для чтения (пока пустой, но сюда можно добавлять маркеры и поиск)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Здесь в будущем можно рисовать подсветку поиска (QGraphicsTextItem)

class ReaderView(BasePDFViewer):
    """Виджет для чтения документов с расширенным тулбаром."""
    
    def _create_view(self):
        # Подменяем базовый View на наш ReadingGraphicsView
        return ReadingGraphicsView(self)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Добавляем панель поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск в документе... (Ctrl+F)")
        self.search_input.setFixedWidth(200)
        # Вставляем поиск в тулбар (индекс 2 - после кнопок move/pick)
        self.toolbar.insertWidget(2, self.search_input)

        # 2. Добавляем кнопки зума и масштабирования
        self.btn_zoom_out = QPushButton("—")
        self.btn_zoom_out.setToolTip("Уменьшить")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setToolTip("Увеличить")
        self.btn_fit_page = QPushButton("[ ]")
        self.btn_fit_page.setToolTip("По размеру окна")

        # Вставляем перед кнопкой "Назад"
        self.toolbar.insertWidget(5, self.btn_zoom_out)
        self.toolbar.insertWidget(6, self.btn_zoom_in)
        self.toolbar.insertWidget(7, self.btn_fit_page)

        # Подключаем кнопки
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_fit_page.clicked.connect(self._fit_to_window)

    def _zoom_in(self):
        self.view.scale(1.25, 1.25)

    def _zoom_out(self):
        self.view.scale(0.8, 0.8)

    def _fit_to_window(self):
        if self.view.scene:
            self.view.fitInView(self.view.scene.sceneRect(), Qt.KeepAspectRatio)