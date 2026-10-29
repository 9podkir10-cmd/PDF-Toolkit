from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QAction, QKeySequence
from PySide6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup, QLabel)
import pymupdf

class BasePDFGraphicsView(QGraphicsView):
    """Базовый вьювер для отображения PDF (без рисования)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignCenter)

        self.current_pixmap = None
        self.dpi = 300
        self.current_pdf_path = None
        self.current_page_num = 0
        self.doc = None

        self.mode = "select"  # "select" or "hand"

    def load_pdf(self, pdf_path: str, page_num: int = 0):
        try:
            current_transform = self.transform()
            self.current_pdf_path = pdf_path
            self.current_page_num = page_num
            if self.doc:
                self.doc.close()
            self.doc = pymupdf.open(pdf_path)
            page = self.doc[page_num]
            pix = page.get_pixmap(dpi=self.dpi)
            img_data = pix.tobytes("ppm")
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            self.current_pixmap = pixmap
            self.pixmap_item.setPixmap(pixmap)
            self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
            if not current_transform.isIdentity():
                self.setTransform(current_transform)
            else:
                self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        except Exception as e:
            print(f"Error loading PDF: {e}")
            self.pixmap_item.setPixmap(QPixmap())
            self.scene.setSceneRect(QRectF(0, 0, 400, 300))
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def current_page(self):
        return self.current_page_num
    
    def get_dpi(self):
        return self.dpi

    def get_total_pages(self) -> int:
        return self.doc.page_count if self.doc else 0

    def go_to_page(self, page_num: int):
        if self.doc and 0 <= page_num < self.doc.page_count:
            self.load_pdf(self.current_pdf_path, page_num)

    def close_document(self):
        if self.doc:
            self.doc.close()
            self.doc = None
            self.update()

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    def set_mode(self, mode: str):
        self.mode = mode
        if mode == "hand":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)


class BasePDFViewer(QWidget):
    """Базовый виджет с тулбаром (навигация и переключение режимов)."""
    forward_requested = Signal()
    backward_requested = Signal()

    def _create_view(self) -> BasePDFGraphicsView:
        """Фабричный метод. Позволяет наследникам подменить View на свой."""
        return BasePDFGraphicsView(self)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = self._create_view()

        # Тулбар
        self.toolbar = QHBoxLayout()
        
        self.btn_hand = QPushButton("move")
        self.btn_hand.setToolTip("H")
        self.btn_select = QPushButton("pick")
        self.btn_select.setToolTip("V")
        
        self.btn_hand.setCheckable(True)
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_hand, 0)
        self.btn_group.addButton(self.btn_select, 1)
        self.btn_group.idClicked.connect(self._on_mode_changed)

        self.btn_back = QPushButton("Назад")
        self.btn_back.setToolTip("Ctrl+Left")
        
        self.counter_label = QLabel("—")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setMinimumWidth(60)
        self.counter_label.setStyleSheet("font-size: 12px; font-weight: bold;")
                
        self.btn_forward = QPushButton("Вперёд")
        self.btn_forward.setToolTip("Ctrl+Right")

        self.toolbar.addWidget(self.btn_hand)
        self.toolbar.addWidget(self.btn_select)
        
        self.toolbar.addStretch()

        self.toolbar.addWidget(self.btn_back)
        self.toolbar.addWidget(self.counter_label)
        self.toolbar.addWidget(self.btn_forward)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)
        layout.addLayout(self.toolbar)
        self.setLayout(layout)

        self.view.set_mode("select")
        self.setup_shortcuts()
        
        self.btn_back.clicked.connect(self._on_backward_clicked)
        self.btn_forward.clicked.connect(self._on_forward_clicked)

    def _on_mode_changed(self, button_id: int):
        if button_id == 0:
            self.view.set_mode("hand")
        else:
            self.view.set_mode("select")

    def setup_shortcuts(self):
        context = Qt.ShortcutContext.WindowShortcut

        action_hand = QAction(self)
        action_hand.setShortcut(QKeySequence("H"))
        action_hand.setShortcutContext(context)
        action_hand.triggered.connect(self.btn_hand.click)
        self.addAction(action_hand)

        action_select = QAction(self)
        action_select.setShortcut(QKeySequence("V"))
        action_select.setShortcutContext(context)
        action_select.triggered.connect(self.btn_select.click)
        self.addAction(action_select)

        action_back = QAction(self)
        action_back.setShortcut(QKeySequence("Ctrl+Left"))
        action_back.setShortcutContext(context)
        action_back.triggered.connect(self.btn_back.click)
        self.addAction(action_back)    
        
        action_forward = QAction(self)
        action_forward.setShortcut(QKeySequence("Ctrl+Right"))
        action_forward.setShortcutContext(context)
        action_forward.triggered.connect(self.btn_forward.click)
        self.addAction(action_forward)            

    def _on_backward_clicked(self):
        self.backward_requested.emit()

    def _on_forward_clicked(self):
        self.forward_requested.emit()  

    # Прокси-методы
    def update_counter(self, current: int, total: int):
        if total == 0:
            self.counter_label.setText("—")
        else:
            self.counter_label.setText(f"{current} / {total}")
    
    def load_pdf(self, pdf_path: str, page_num: int = 0):
        self.view.load_pdf(pdf_path, page_num)

    def get_total_pages(self) -> int:
        return self.view.get_total_pages()

    def go_to_page(self, page_num: int):
        self.view.go_to_page(page_num)

    def close_document(self):
        self.view.close_document()

    def wheelEvent(self, event):
        self.view.wheelEvent(event)

    def get_dpi(self):
        return self.view.get_dpi()

    def current_page(self):
        return self.view.current_page()