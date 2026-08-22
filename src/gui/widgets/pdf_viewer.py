from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
import fitz


class PDFViewer(QGraphicsView):
    rect_selected = Signal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Настройки
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignCenter)

        self.drawn_items = []
        self.colors = [
            QColor(255, 0, 0),      # Красный
            QColor(0, 255, 0),      # Зеленый
            QColor(0, 0, 255),      # Синий
            QColor(255, 165, 0),    # Оранжевый
            QColor(128, 0, 128),    # Фиолетовый
            QColor(255, 20, 147),   # Розовый
        ]        
        
        self.rubber_band = None
        self.origin = None
        self.current_pixmap = None
        self.dpi = 150
        self.current_pdf_path = None
        self.current_page_num = 0
        self.doc = None

        self.selection_pen = QPen(QColor(255, 0, 0, 200), 2, Qt.DashLine)

    def load_pdf(self, pdf_path: str, page_num: int = 0):
        try:
            self.current_pdf_path = pdf_path
            self.current_page_num = page_num

            if self.doc:
                self.doc.close()

            self.doc = fitz.open(pdf_path)
            page = self.doc[page_num]
            pix = page.get_pixmap(dpi=self.dpi)

            img_data = pix.tobytes("ppm")
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)

            self.current_pixmap = pixmap
            self.pixmap_item.setPixmap(pixmap)
            self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

            self.clear_selection()

        except Exception as e:
            print(f"Error loading PDF: {e}")
            self.pixmap_item.setPixmap(QPixmap())
            self.scene.setSceneRect(QRectF(0, 0, 400, 300))
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def get_total_pages(self) -> int:
        if self.doc:
            return self.doc.page_count
        return 0

    def go_to_page(self, page_num: int):
        if self.doc and 0 <= page_num < self.doc.page_count:
            self.load_pdf(self.current_pdf_path, page_num)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            
            self.rubber_band = self.scene.addRect(
                0, 0, 0, 0,
                self.selection_pen,
                QColor(255, 0, 0, 50)
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        if event.button() == Qt.LeftButton and self.rubber_band:
            rect = self.rubber_band.rect()
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

            if w > 5 and h > 5:  # минимальный размер
                color_index = len(self.drawn_items) % len(self.colors)
                color = self.colors[color_index]
                
                permanent_item = QGraphicsRectItem(rect)
                pen = QPen(color, 3) # Толщина 3px, сплошной стиль
                pen.setStyle(Qt.SolidLine)
                permanent_item.setPen(pen)
                
                self.scene.addItem(permanent_item)
                self.drawn_items.append(permanent_item) # Сохраняем в список
                
                page_num_display = self.current_page_num + 1
                self.rect_selected.emit(int(x), int(y), int(w), int(h), page_num_display)
                
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

    def close_document(self):
        if hasattr(self, 'doc') and self.doc:
            self.doc.close()
            self.doc = None
            self.update()

    def get_selected_area(self) -> tuple:
        if self.rubber_band:
            rect = self.rubber_band.rect()
            return (rect.x(), rect.y(), rect.width(), rect.height())
        return None

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)