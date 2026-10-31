import os
from pathlib import Path

import pymupdf
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from backend.constants import RENDER_DPI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "assets", "icons"))
ICON_LEFT = os.path.join(ICONS_DIR, "arrows/left_arrow.svg")
ICON_RIGHT = os.path.join(ICONS_DIR, "arrows/right_arrow.svg")
ICON_MINUS = os.path.join(ICONS_DIR, "BasePDFViewer/minus.svg")
ICON_PLUS = os.path.join(ICONS_DIR, "BasePDFViewer/plus.svg")
ICON_FIT = os.path.join(ICONS_DIR, "BasePDFViewer/page_fit.svg")
ICON_HAND = os.path.join(ICONS_DIR, "BasePDFViewer/hand.svg")
ICON_CURSOR = os.path.join(ICONS_DIR, "BasePDFViewer/cursor.svg")


class BasePDFGraphicsView(QGraphicsView):
    page_changed = Signal(int, int) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.set_mode("hand")
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignCenter)

        self.current_pixmap = None
        self.dpi = RENDER_DPI
        self.current_pdf_path = None
        self.current_page_num = 0
        self.doc = None

    def load_pdf(self, pdf_path: str, page_num: int = 0):
        try:
            current_transform = self.transform() 
            pdf_bytes = Path(pdf_path).read_bytes()
            self.doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            
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
                
            total = self.doc.page_count if self.doc else 0
            self.page_changed.emit(page_num + 1, total) 
            
        except Exception:
            self.pixmap_item.setPixmap(QPixmap())
            self.scene.setSceneRect(QRectF(0, 0, 400, 300))
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def current_page(self):
        return self.current_page_num
    
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
    def _create_view(self):
        return BasePDFGraphicsView(self)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = self._create_view()

        self._build_ui()
        self._connect_signals()
        self.setup_shortcuts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.top_toolbar = QWidget()
        self.top_toolbar.setObjectName("pdfTopToolbar")
        toolbar_layout = QHBoxLayout(self.top_toolbar)
        toolbar_layout.setContentsMargins(15, 5, 15, 5)
        toolbar_layout.setSpacing(8)

        self.btn_prev_page = QPushButton()
        self.btn_prev_page.setIcon(QIcon(ICON_LEFT))
        self.btn_prev_page.setFixedSize(28, 28)

        self.page_spin = QSpinBox()
        self.page_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.page_spin.setFixedWidth(40)
        self.page_spin.setAlignment(Qt.AlignCenter)

        self.lbl_total_pages = QLabel("/ 0")
        self.lbl_total_pages.setAlignment(Qt.AlignCenter)
        self.lbl_total_pages.setFixedWidth(30)

        self.btn_next_page = QPushButton()
        self.btn_next_page.setIcon(QIcon(ICON_RIGHT))
        self.btn_next_page.setFixedSize(28, 28)

        toolbar_layout.addWidget(self.btn_prev_page)
        toolbar_layout.addWidget(self.page_spin)
        toolbar_layout.addWidget(self.lbl_total_pages)
        toolbar_layout.addWidget(self.btn_next_page)

        toolbar_layout.addStretch(1)

        self.btn_zoom_out = QPushButton()
        self.btn_zoom_out.setIcon(QIcon(ICON_MINUS))
        self.btn_zoom_out.setFixedSize(28, 28)
        
        self.zoom_combo = QComboBox()
        self.zoom_combo.setFixedWidth(80)
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "Fit Page"])
        self.zoom_combo.setCurrentText("Fit Page")

        self.btn_zoom_in = QPushButton()
        self.btn_zoom_in.setIcon(QIcon(ICON_PLUS))
        self.btn_zoom_in.setFixedSize(28, 28)
        
        self.btn_fit_page = QPushButton()
        self.btn_fit_page.setIcon(QIcon(ICON_FIT))
        self.btn_fit_page.setFixedSize(28, 28)
        self.btn_fit_page.setToolTip("Fit to Page")

        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.zoom_combo)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.btn_fit_page)

        toolbar_layout.addStretch(1)

        self.btn_hand = QPushButton()
        self.btn_hand.setIcon(QIcon(ICON_HAND))
        self.btn_hand.setFixedSize(28, 28)
        self.btn_hand.setCheckable(True)
        self.btn_hand.setChecked(True)
        
        self.btn_select = QPushButton()
        self.btn_select.setIcon(QIcon(ICON_CURSOR))
        self.btn_select.setFixedSize(28, 28)
        self.btn_select.setCheckable(True)

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_hand, 0)
        self.btn_group.addButton(self.btn_select, 1)
        
        toolbar_layout.addWidget(self.btn_hand)
        toolbar_layout.addWidget(self.btn_select)

        self.custom_tools_layout = QHBoxLayout()
        self.custom_tools_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.addLayout(self.custom_tools_layout)

        layout.addWidget(self.top_toolbar)
        layout.addWidget(self.view, 1)

    def _connect_signals(self):
        self.btn_prev_page.clicked.connect(self._prev_page)
        self.btn_next_page.clicked.connect(self._next_page)
        self.page_spin.valueChanged.connect(self._page_changed)
        
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_fit_page.clicked.connect(self._fit_page)
        self.zoom_combo.currentTextChanged.connect(self._zoom_combo_changed)
        
        self.btn_group.idClicked.connect(self._on_mode_changed)
        
        self.view.page_changed.connect(self._on_view_page_changed)

    # --- навигация по страницам ---
    def _prev_page(self):
        current = self.view.current_page()
        if current > 0:
            self.view.go_to_page(current - 1)

    def _next_page(self):
        current = self.view.current_page()
        total = self.view.get_total_pages()
        if current < total - 1:
            self.view.go_to_page(current + 1)

    def _page_changed(self, value):
        self.view.go_to_page(value - 1)

    def _on_view_page_changed(self, current: int, total: int):
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(total if total > 0 else 1)
        self.page_spin.setValue(current)
        self.page_spin.blockSignals(False)
        
        self.lbl_total_pages.setText(f"/ {total}")
        self.btn_prev_page.setEnabled(current > 1)
        self.btn_next_page.setEnabled(current < total)

    # --- зум ---
    def _zoom_in(self):
        self.view.scale(1.25, 1.25)
        self.zoom_combo.setCurrentText("Custom")

    def _zoom_out(self):
        self.view.scale(0.8, 0.8)
        self.zoom_combo.setCurrentText("Custom")

    def _fit_page(self):
        self.view.fitInView(self.view.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_combo.setCurrentText("Fit Page")

    def _zoom_combo_changed(self, text):
        if text == "Fit Page":
            self._fit_page()
        elif text == "Custom":
            pass
        else:
            try:
                factor = int(text.replace("%", "")) / 100.0
                self.view.resetTransform()
                self.view.scale(factor, factor)
            except ValueError:
                pass

    # --- Режимы ---
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

    # --- Прокси-методы ---
    def load_pdf(self, pdf_path: str, page_num: int = 0):
        self.view.load_pdf(pdf_path, page_num)

    def get_total_pages(self) -> int:
        return self.view.get_total_pages()

    def go_to_page(self, page_num: int):
        self.view.go_to_page(page_num)

    def close_document(self):
        self.view.close_document()

    def current_page(self):
        return self.view.current_page()