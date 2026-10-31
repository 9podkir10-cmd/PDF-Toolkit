from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class IndexToolsPanel(QWidget):
    ocr_requested = Signal()
    clear_requested = Signal()
    apply_requested = Signal()
    template_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("indexToolsPanel")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # ---- ocr buttons ----
        ocr_row = QHBoxLayout()
        self.ocr_button = QPushButton("Распознать выделенную область")
        self.ocr_button.setMinimumHeight(40)
        self.ocr_button.setEnabled(False)
        self.ocr_button.clicked.connect(self.ocr_requested.emit)
        ocr_row.addWidget(self.ocr_button, 4)

        self.auto_ocr_checkbox = QCheckBox("Auto")
        self.auto_ocr_checkbox.setChecked(False)
        ocr_row.addWidget(self.auto_ocr_checkbox, 1)
        layout.addLayout(ocr_row)

        self.clear_button = QPushButton("Отменить выделение")
        self.clear_button.setToolTip("Esc")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        layout.addWidget(self.clear_button)
        layout.addSpacing(10)

        # ---- результат распознавания ----
        self.ocr_info = QLabel("Выделено областей: 0")
        layout.addWidget(self.ocr_info)
        
        self.result_text = QPlainTextEdit()
        self.result_text.setPlaceholderText("Здесь появится распознанный текст...")
        layout.addWidget(self.result_text, 1)

        # ---- Rename templates ----
        layout.addWidget(QLabel("Шаблон переименования:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("Не использовать", -1)
        self.template_combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.template_combo)

        # ---- имя файла ----
        layout.addWidget(QLabel("Имя файла"))
        self.filename_edit = QLineEdit()
        layout.addWidget(self.filename_edit)

        # ---- Apply button ----
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Enter")
        self.apply_btn.setMinimumHeight(42)
        self.apply_btn.clicked.connect(self.apply_requested.emit)
        layout.addWidget(self.apply_btn)

    def _on_combo_changed(self, index):
        self.template_changed.emit(self.template_combo.currentData())

    # --- Прокси-методы для управления из Ocr_fPage ---
    def set_ocr_running(self, running: bool):
        self.apply_btn.setEnabled(not running)
        self.ocr_button.setEnabled(not running and "0" not in self.ocr_info.text())

    def set_zones_count(self, count: int):
        self.ocr_info.setText(f"Выделено областей: {count}")
        self.ocr_button.setEnabled(count > 0)

    def set_result_text(self, text: str):
        self.result_text.setPlainText(text)
        
    def append_result_text(self, text: str):
        self.result_text.appendPlainText(text)
        
    def get_result_text(self) -> str:
        return self.result_text.toPlainText()

    def set_filename(self, name: str):
        self.filename_edit.setText(name)
        
    def get_filename(self) -> str:
        return self.filename_edit.text().strip()

    def update_templates(self, templates, selected_idx):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("Не использовать", -1)
        for idx, tpl in enumerate(templates):
            self.template_combo.addItem(tpl.name or tpl.pattern, idx)
            
        found = -1
        for i in range(self.template_combo.count()):
            if self.template_combo.itemData(i) == selected_idx:
                found = i
                break
        self.template_combo.setCurrentIndex(max(found, 0))
        self.template_combo.blockSignals(False)

    def is_auto_ocr_checked(self) -> bool:
        return self.auto_ocr_checkbox.isChecked()