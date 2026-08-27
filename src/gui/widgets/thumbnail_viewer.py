from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout,
    QScrollArea, QMenu, QInputDialog, QMessageBox
)
from PIL import Image

from backend.scanning.models import Batch, Document, Page


def pil_to_pixmap(pil_image: Image.Image, max_size: int = 120) -> QPixmap:
    """Конвертирует PIL Image в QPixmap с изменением размера."""
    thumb = pil_image.copy()
    thumb.thumbnail((max_size, max_size), Image.LANCZOS)

    if thumb.mode == "RGB":
        data = thumb.tobytes("raw", "RGB")
        qimage = QImage(data, thumb.width, thumb.height, QImage.Format_RGB888)
    else:
        thumb_rgb = thumb.convert('RGB')
        data = thumb_rgb.tobytes("raw", "RGB")
        qimage = QImage(data, thumb_rgb.width, thumb_rgb.height, QImage.Format_RGB888)

    return QPixmap.fromImage(qimage)


class ThumbnailWidget(QLabel):
    """Миниатюра одной страницы с контекстным меню."""

    page_removed = Signal(object)
    page_moved_up = Signal(object)
    page_moved_down = Signal(object)
    page_rotated = Signal(object, int)
    page_moved_to_doc = Signal(object, int)

    def __init__(self, page: Page, doc_index: int, batch: Batch, parent=None):
        super().__init__(parent)
        self.page = page
        self.doc_index = doc_index
        self.batch = batch
        self.setFixedSize(130, 160)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        self.setToolTip(f"Стр. {page.page_number}")
        self.update_thumbnail()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_thumbnail(self):
        pixmap = pil_to_pixmap(self.page.image, max_size=120)
        self.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_context_menu(self, pos):
        menu = QMenu(self)

        move_up = QAction("Переместить вверх", self)
        move_up.triggered.connect(lambda: self.page_moved_up.emit(self))
        menu.addAction(move_up)

        move_down = QAction("Переместить вниз", self)
        move_down.triggered.connect(lambda: self.page_moved_down.emit(self))
        menu.addAction(move_down)

        move_to_doc = QAction("Переместить в другой документ...", self)
        move_to_doc.triggered.connect(self.move_to_another_document)
        menu.addAction(move_to_doc)

        menu.addSeparator()

        rotate_90 = QAction("Повернуть на 90°", self)
        rotate_90.triggered.connect(lambda: self.page_rotated.emit(self, 90))
        menu.addAction(rotate_90)

        rotate_180 = QAction("Повернуть на 180°", self)
        rotate_180.triggered.connect(lambda: self.page_rotated.emit(self, 180))
        menu.addAction(rotate_180)

        rotate_270 = QAction("Повернуть на 270°", self)
        rotate_270.triggered.connect(lambda: self.page_rotated.emit(self, 270))
        menu.addAction(rotate_270)

        menu.addSeparator()

        delete_action = QAction("Удалить страницу", self)
        delete_action.triggered.connect(lambda: self.page_removed.emit(self))
        menu.addAction(delete_action)

        menu.exec_(self.mapToGlobal(pos))

    def move_to_another_document(self):
        if len(self.batch.documents) <= 1:
            QMessageBox.information(self, "Информация", "В Batch только один документ.")
            return

        doc_names = [f"Документ {i+1}" for i in range(len(self.batch.documents))]
        current_doc = self.doc_index
        items = [f"{i+1}: {name}" for i, name in enumerate(doc_names) if i != current_doc]
        if not items:
            QMessageBox.information(self, "Информация", "Нет других документов.")
            return

        item, ok = QInputDialog.getItem(
            self,
            "Переместить страницу",
            "Выберите целевой документ:",
            items,
            0,
            False
        )
        if ok and item:
            target_index = int(item.split(":")[0]) - 1
            self.page_moved_to_doc.emit(self, target_index)


class DocumentGroup(QGroupBox):
    """Группа страниц одного документа."""

    def __init__(self, doc_index: int, batch: Batch, batch_preview, parent=None):
        super().__init__(f"Документ {doc_index+1}", parent)
        self.doc_index = doc_index
        self.batch = batch
        self.batch_preview = batch_preview
        self.thumbnails = []
        self.layout = QGridLayout(self)
        self.layout.setSpacing(5)
        self.update_display()

    def update_display(self):
        # Отключаем все сигналы от старых виджетов и удаляем их
        for thumb in self.thumbnails:
            thumb.page_removed.disconnect()
            thumb.page_moved_up.disconnect()
            thumb.page_moved_down.disconnect()
            thumb.page_rotated.disconnect()
            thumb.page_moved_to_doc.disconnect()
            self.layout.removeWidget(thumb)
            thumb.deleteLater()
        self.thumbnails.clear()

        doc = self.batch.documents[self.doc_index]
        for i, page in enumerate(doc.pages):
            thumb = ThumbnailWidget(page, self.doc_index, self.batch)
            thumb.page_removed.connect(self.on_page_removed)
            thumb.page_moved_up.connect(self.on_page_moved_up)
            thumb.page_moved_down.connect(self.on_page_moved_down)
            thumb.page_rotated.connect(self.on_page_rotated)
            thumb.page_moved_to_doc.connect(self.on_page_moved_to_doc)
            self.layout.addWidget(thumb, i // 4, i % 4)
            self.thumbnails.append(thumb)

    def on_page_removed(self, thumb: ThumbnailWidget):
        doc = self.batch.documents[self.doc_index]
        if thumb.page in doc.pages:
            doc.pages.remove(thumb.page)
            self._renumber_pages()
            self.batch_preview.rebuild_all()

    def on_page_moved_up(self, thumb: ThumbnailWidget):
        doc = self.batch.documents[self.doc_index]
        pages = doc.pages
        try:
            idx = pages.index(thumb.page)
            if idx > 0:
                pages[idx], pages[idx-1] = pages[idx-1], pages[idx]
                self._renumber_pages()
                self.batch_preview.rebuild_all()
        except ValueError:
            pass

    def on_page_moved_down(self, thumb: ThumbnailWidget):
        doc = self.batch.documents[self.doc_index]
        pages = doc.pages
        try:
            idx = pages.index(thumb.page)
            if idx < len(pages) - 1:
                pages[idx], pages[idx+1] = pages[idx+1], pages[idx]
                self._renumber_pages()
                self.batch_preview.rebuild_all()
        except ValueError:
            pass

    def on_page_rotated(self, thumb: ThumbnailWidget, angle: int):
        rotated = thumb.page.image.rotate(angle, expand=True)
        thumb.page.image = rotated
        thumb.update_thumbnail()

    def on_page_moved_to_doc(self, thumb: ThumbnailWidget, target_doc_index: int):
        if target_doc_index == self.doc_index:
            return

        doc = self.batch.documents[self.doc_index]
        if thumb.page not in doc.pages:
            return
        doc.pages.remove(thumb.page)

        target_doc = self.batch.documents[target_doc_index]
        target_doc.pages.append(thumb.page)

        self.batch_preview.rebuild_all()

    def _renumber_pages(self):
        doc = self.batch.documents[self.doc_index]
        for i, page in enumerate(doc.pages):
            page.page_number = i + 1


class BatchPreviewWidget(QWidget):
    """Виджет для отображения Batch'а с группировкой по документам."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._batch = None

        self.main_layout = QVBoxLayout(self)
        self.batch_label = QLabel("Batch: Не загружен")
        self.main_layout.addWidget(self.batch_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

    def display_batch(self, batch: Batch):
        self._batch = batch
        self.rebuild_all()

    def rebuild_all(self):
        """Полностью перестраивает интерфейс из текущего _batch."""
        if self._batch is None:
            return

        # Очищаем scroll_layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        total_pages = sum(len(doc.pages) for doc in self._batch.documents)
        self.batch_label.setText(
            f"Batch: {self._batch.name} (Документов: {len(self._batch.documents)}, Страниц: {total_pages})"
        )

        for idx, doc in enumerate(self._batch.documents):
            group = DocumentGroup(idx, self._batch, self)
            self.scroll_layout.addWidget(group)

        self.scroll_layout.addStretch()

    def get_batch(self) -> Batch:
        return self._batch

    def clear_batch(self):
        self._batch = None
        self.batch_label.setText("Batch: Не загружен")
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()