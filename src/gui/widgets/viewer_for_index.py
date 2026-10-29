from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPen, QColor, QAction, QKeySequence
from PySide6.QtWidgets import QPushButton, QGraphicsRectItem
from backend.services.box_to_img import Region

from gui.widgets.pdf_viewer import BasePDFGraphicsView, BasePDFViewer

class PDFGraphicsView(BasePDFGraphicsView):
    """Вьювер для индексации: умеет рисовать прямоугольники."""
    rect_selected = Signal(Region)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Логика, специфичная для рисования
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
        self.selection_pen = QPen(QColor(255, 0, 0, 200), 2, Qt.DashLine)

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

    def get_selected_area(self):
        if self.rubber_band:
            rect = self.rubber_band.rect()
            return (rect.x(), rect.y(), rect.width(), rect.height())
        return None


class PDFViewer(BasePDFViewer):
    """Виджет для индексации. Добавляет кнопку Lock к базовому тулбару."""
    rect_selected = Signal(Region)
    lock_toggled = Signal(bool) 

    def _create_view(self):
        # Подменяем базовый View на наш, который умеет рисовать
        view = PDFGraphicsView(self)
        view.rect_selected.connect(self.rect_selected)
        return view

    def __init__(self, parent=None):
        super().__init__(parent)

        # Добавляем специфичную для индексации кнопку Lock
        self.btn_lock = QPushButton("Lock")
        self.btn_lock.setToolTip("Ctrl + L")
        self.btn_lock.setCheckable(True)
        
        # Вставляем кнопку Lock после кнопки Select (индекс 2)
        self.toolbar.insertWidget(2, self.btn_lock)

        self.btn_lock.clicked.connect(self._on_lock_clicked)
        self.setup_extra_shortcuts()

    def setup_extra_shortcuts(self):
        context = Qt.ShortcutContext.WindowShortcut
        action_lock = QAction(self)
        action_lock.setShortcut(QKeySequence("Ctrl+L"))
        action_lock.setShortcutContext(context)
        action_lock.triggered.connect(self.btn_lock.click)
        self.addAction(action_lock)

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

    # Специфичные для индексации прокси-методы
    def clear_selection(self):
        self.view.clear_selection()

    def remove_last_rect(self):
        return self.view.remove_last_rect()

    def get_selected_area(self):
        return self.view.get_selected_area()

    def set_rects(self, rects):
        self.view.set_rects(rects)