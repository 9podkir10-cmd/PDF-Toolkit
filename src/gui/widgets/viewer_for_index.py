import os
from PySide6.QtCore import Qt, QRectF, QRect, QSize, Signal
from PySide6.QtGui import QColor, QPen, QAction, QKeySequence, QIcon
from PySide6.QtWidgets import QGraphicsRectItem, QRubberBand, QPushButton
from backend.services.box_to_img import Region
from gui.widgets.pdf_viewer import BasePDFGraphicsView, BasePDFViewer

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "assets", "icons"))
ICON_LOCK = os.path.join(ICONS_DIR, "BasePDFViewer/lock.svg")
ICON_LOCK_OPEN = os.path.join(ICONS_DIR, "BasePDFViewer/lock_open.svg")


class IndexGraphicsView(BasePDFGraphicsView):
    rect_selected = Signal(Region)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawn_items = []
        self.origin = None
        
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self.rubber_band.setStyleSheet("QRubberBand {border: 2px dashed red; background-color: rgba(255, 0, 0, 50);}")

    @property
    def _pdf_to_screen_scale(self) -> float:
        return self.dpi / 72.0

    @property
    def _screen_to_pdf_scale(self) -> float:
        return 72.0 / self.dpi

    def _get_color_for_index(self, index: int) -> QColor:
        golden_ratio_conjugate = 0.618033988749895
        hue = (index * golden_ratio_conjugate + 0.5) % 1.0
        return QColor.fromHsvF(hue, 0.8, 0.9)

    def _draw_rect(self, rect: QRectF):
        color = self._get_color_for_index(len(self.drawn_items))
        
        rect_item = QGraphicsRectItem(rect)
        pen = QPen(color, 3)
        pen.setStyle(Qt.SolidLine)
        pen.setCosmetic(True) 
        rect_item.setPen(pen)
        
        fill_color = QColor(color)
        fill_color.setAlpha(40)
        rect_item.setBrush(fill_color)
        
        self.scene.addItem(rect_item)
        self.drawn_items.append(rect_item)

    def set_rects(self, regions):
        self.rubber_band.hide()
        self.origin = None
        
        for item in self.drawn_items:
            self.scene.removeItem(item)
        self.drawn_items.clear()

        scale = self._pdf_to_screen_scale
        for r in regions:
            x = r.x * scale
            y = r.y * scale
            w = r.w * scale
            h = r.h * scale
            
            self._draw_rect(QRectF(x, y, w, h))
            
    def _to_pdf_coords(self, rect: QRectF) -> tuple:
        scale = self._screen_to_pdf_scale
        return (
            rect.x() * scale,
            rect.y() * scale,
            rect.width() * scale,
            rect.height() * scale
        )

    def mousePressEvent(self, event):
        if self.mode == "hand":
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == "hand":
            super().mouseMoveEvent(event)
            return
            
        if self.rubber_band.isVisible() and self.origin:
            # Обновляем геометрию (координаты виджета)
            rect = QRect(self.origin, event.pos()).normalized()
            self.rubber_band.setGeometry(rect)
            
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "hand":
            super().mouseReleaseEvent(event)
            return
        
        if event.button() == Qt.LeftButton and self.rubber_band.isVisible():
            self.rubber_band.hide()
            widget_rect = self.rubber_band.geometry()
            
            if widget_rect.width() > 5 and widget_rect.height() > 5:
                scene_rect = self.mapToScene(widget_rect).boundingRect()
                self._draw_rect(scene_rect)
                
                pdf_x, pdf_y, pdf_w, pdf_h = self._to_pdf_coords(scene_rect)
                region = Region(
                    page=self.current_page_num + 1,
                    x=pdf_x, y=pdf_y, w=pdf_w, h=pdf_h
                )
                self.rect_selected.emit(region)
            self.origin = None
        super().mouseReleaseEvent(event)

    def clear_selection(self):
        self.rubber_band.hide()
        for item in self.drawn_items:
            self.scene.removeItem(item)
        self.drawn_items.clear()
        self.origin = None

    def remove_last_rect(self):
        if self.drawn_items:
            item = self.drawn_items.pop()
            self.scene.removeItem(item)
            return True
        return False

    def get_selected_area(self):
        if self.rubber_band.isVisible():
            rect = self.rubber_band.geometry()
            return (rect.x(), rect.y(), rect.width(), rect.height())
        return None


class IndexViewer(BasePDFViewer):
    rect_selected = Signal(Region)
    lock_toggled = Signal(bool) 

    def _create_view(self):
        view = IndexGraphicsView(self)
        view.rect_selected.connect(self.rect_selected)
        return view

    def __init__(self, parent=None):
        super().__init__(parent)

        self.btn_lock = QPushButton()
        self.btn_lock.setIcon(QIcon(ICON_LOCK_OPEN))
        self.btn_lock.setFixedSize(28, 28)
        self.btn_lock.setToolTip("Ctrl + L")
        self.btn_lock.setCheckable(True)
        
        self.custom_tools_layout.addWidget(self.btn_lock)

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
        
        if checked:
            self.btn_lock.setIcon(QIcon(ICON_LOCK))
            self.btn_lock.setToolTip("Unlock (Ctrl+L)")
        else:
            self.btn_lock.setIcon(QIcon(ICON_LOCK_OPEN))
            self.btn_lock.setToolTip("Lock (Ctrl+L)")
        
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

    # прокси-методы
    def clear_selection(self):
        self.view.clear_selection()

    def remove_last_rect(self):
        return self.view.remove_last_rect()

    def get_selected_area(self):
        return self.view.get_selected_area()

    def set_rects(self, regions):
        self.view.set_rects(regions)