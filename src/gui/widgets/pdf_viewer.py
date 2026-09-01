from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QAction, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup
)
import pymupdf
from backend.services.box_to_img import Region

class PDFGraphicsView(QGraphicsView):
    rect_selected = Signal(Region)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignCenter)

        self.drawn_items = []
        self.colors = [
            QColor(255, 0, 0),
            QColor(0, 255, 0),
            QColor(0, 0, 255),
            QColor(255, 165, 0),
            QColor(128, 0, 128),
            QColor(255, 20, 147),
        ]

        self.rubber_band = None
        self.origin = None
        self.current_pixmap = None
        self.dpi = 300
        self.current_pdf_path = None
        self.current_page_num = 0
        self.doc = None
        self.selection_pen = QPen(QColor(255, 0, 0, 200), 2, Qt.DashLine)

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

    def set_rects(self, rects):
        for item in self.drawn_items:
            self.scene.removeItem(item)
        self.drawn_items.clear()

        for i, (x, y, w, h) in enumerate(rects):
            color_index = i % len(self.colors)
            color = self.colors[color_index]
            rect_item = QGraphicsRectItem(QRectF(x, y, w, h))
            pen = QPen(color, 3)
            pen.setStyle(Qt.SolidLine)
            rect_item.setPen(pen)
            self.scene.addItem(rect_item)
            self.drawn_items.append(rect_item)

    def current_page(self):
        return self.current_page_num
    
    def get_dpi(self):
        return self.dpi

    def get_total_pages(self) -> int:
        return self.doc.page_count if self.doc else 0

    def go_to_page(self, page_num: int):
        if self.doc and 0 <= page_num < self.doc.page_count:
            self.load_pdf(self.current_pdf_path, page_num)

    def mousePressEvent(self, event):
        if self.mode == "hand":
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band = self.scene.addRect(0, 0, 0, 0, self.selection_pen, QColor(255, 0, 0, 50))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == "hand":
            super().mouseMoveEvent(event)
            return
        if self.rubber_band and self.origin:
            rect = QRectF(
                min(self.origin.x(), event.pos().x()),
                min(self.origin.y(), event.pos().y()),
                abs(self.origin.x() - event.pos().x()),
                abs(self.origin.y() - event.pos().y())
            )
            scene_rect = self.mapToScene(rect.toRect()).boundingRect()
            self.rubber_band.setRect(scene_rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "hand":
            super().mouseReleaseEvent(event)
            return
        if event.button() == Qt.LeftButton and self.rubber_band:
            rect = self.rubber_band.rect()
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            if w > 5 and h > 5:
                color_index = len(self.drawn_items) % len(self.colors)
                color = self.colors[color_index]
                permanent_item = QGraphicsRectItem(rect)
                pen = QPen(color, 3)
                pen.setStyle(Qt.SolidLine)
                permanent_item.setPen(pen)
                self.scene.addItem(permanent_item)
                self.drawn_items.append(permanent_item)

                # Преобразование в PDF-координаты
                scale = 72 / self.dpi
                region = Region(
                    page=self.current_page_num + 1,
                    x=x * scale,
                    y=y * scale,
                    w=w * scale,
                    h=h * scale
                )
                self.rect_selected.emit(region)

                self.scene.removeItem(self.rubber_band)
                self.rubber_band = None
                self.origin = None
            else:
                self.clear_selection()
        super().mouseReleaseEvent(event)

    def clear_selection(self):
        for item in self.drawn_items:
            self.scene.removeItem(item)
        self.drawn_items.clear()
        if self.rubber_band:
            self.scene.removeItem(self.rubber_band)
            self.rubber_band = None
        self.origin = None

    def remove_last_rect(self):
        if self.drawn_items:
            item = self.drawn_items.pop()
            self.scene.removeItem(item)
            return True
        return False

    def close_document(self):
        if self.doc:
            self.doc.close()
            self.doc = None
            self.update()

    def get_selected_area(self):
        if self.rubber_band:
            rect = self.rubber_band.rect()
            return (rect.x(), rect.y(), rect.width(), rect.height())
        return None

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    def set_mode(self, mode: str):
        self.mode = mode
        if mode == "hand":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)

class PDFViewer(QWidget):
    rect_selected = Signal(Region)
    lock_toggled = Signal(bool)     
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = PDFGraphicsView(self)
        self.view.rect_selected.connect(self.rect_selected)

        # Тулбар
        self.toolbar = QHBoxLayout()
        self.btn_back = QPushButton("Назад")
        self.btn_back.setToolTip("Ctrl+Left")
        self.btn_forward = QPushButton("Вперёд")
        self.btn_forward.setToolTip("Ctrl+Right")

        self.btn_hand = QPushButton("move")
        self.btn_hand.setToolTip("H")
        self.btn_select = QPushButton("pick")
        self.btn_select.setToolTip("V")
        self.btn_lock = QPushButton("Lock")
        self.btn_lock.setToolTip("Ctrl + L")
        self.btn_lock.setCheckable(True)
        self.btn_hand.setCheckable(True)
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_hand, 0)
        self.btn_group.addButton(self.btn_select, 1)
        self.btn_group.idClicked.connect(self._on_mode_changed)

        self.toolbar.addWidget(self.btn_hand)
        self.toolbar.addWidget(self.btn_select)
        self.toolbar.addWidget(self.btn_lock)

        self.toolbar.addStretch()

        self.toolbar.addWidget(self.btn_back)
        self.toolbar.addWidget(self.btn_forward)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)
        layout.addLayout(self.toolbar)
        self.setLayout(layout)

        self.view.set_mode("select")
        self.btn_lock.clicked.connect(self._on_lock_clicked)
        self.btn_back.clicked.connect(self.go_back_file)
        self.btn_forward.clicked.connect(self.go_forward_file)
        self.setup_shortcuts()

    def _on_mode_changed(self, button_id: int):
        if button_id == 0:
            self.view.set_mode("hand")
        else:
            self.view.set_mode("select")

    def setup_shortcuts(self):
        context = Qt.ShortcutContext.WindowShortcut

        # H – режим "рука" (перемещение)
        action_hand = QAction(self)
        action_hand.setShortcut(QKeySequence("H"))
        action_hand.setShortcutContext(context)
        action_hand.triggered.connect(self.btn_hand.click)
        self.addAction(action_hand)

        # V – режим "выделение"
        action_select = QAction(self)
        action_select.setShortcut(QKeySequence("V"))
        action_select.setShortcutContext(context)
        action_select.triggered.connect(self.btn_select.click)
        self.addAction(action_select)

        # Ctrl+L – блокировка (глобально для окна)
        action_lock = QAction(self)
        action_lock.setShortcut(QKeySequence("Ctrl+L"))
        action_lock.setShortcutContext(context)
        action_lock.triggered.connect(self.btn_lock.click)
        self.addAction(action_lock)
        
        # Ctrl+Left – предыдущий файл
        action_back = QAction(self)
        action_back.setShortcut(QKeySequence("Ctrl+Left"))
        action_back.setShortcutContext(context)
        action_back.triggered.connect(self.btn_back.click)
        self.addAction(action_back)    
        
        # Ctrl+Right – следующий файл
        action_forward = QAction(self)
        action_forward.setShortcut(QKeySequence("Ctrl+Right"))
        action_forward.setShortcutContext(context)
        action_forward.triggered.connect(self.btn_forward.click)
        self.addAction(action_forward)            

    def _on_lock_clicked(self):
        checked = self.btn_lock.isChecked()
        self.set_lock_mode(checked)
        self.lock_toggled.emit(checked)

    def set_lock_mode(self, locked):
        self.btn_select.setEnabled(not locked)
        self.btn_hand.setEnabled(True)
        if locked:
            self.btn_hand.setChecked(True)
            self.view.set_mode("hand")
        else:
            self.btn_select.setChecked(True)
            self.view.set_mode("select")
            
    def go_back_file(self):
        print("Использование1")
    
    def go_forward_file(self):
        print("Использование2")     

    # Прокси-методы
    def load_pdf(self, pdf_path: str, page_num: int = 0):
        self.view.load_pdf(pdf_path, page_num)

    def get_total_pages(self) -> int:
        return self.view.get_total_pages()

    def go_to_page(self, page_num: int):
        self.view.go_to_page(page_num)

    def clear_selection(self):
        self.view.clear_selection()

    def remove_last_rect(self):
        return self.view.remove_last_rect()

    def close_document(self):
        self.view.close_document()

    def get_selected_area(self):
        return self.view.get_selected_area()

    def wheelEvent(self, event):
        self.view.wheelEvent(event)

    def get_dpi(self):
        return self.view.get_dpi()

    def set_rects(self, rects):
        self.view.set_rects(rects)

    def current_page(self):
        return self.view.current_page()