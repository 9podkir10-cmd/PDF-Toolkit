from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QFileDialog,
    QButtonGroup,
    QSizePolicy,
    QCheckBox,
    QListWidget,
    QDialog,
    QListWidgetItem,
    QDialogButtonBox,
)
from typing import Optional
from backend.config import load_config, save_main_settings, id_to_lang_string, get_config_path, get_templates, save_templates, set_selected_template_index, get_selected_template_index

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_config = load_config()
        self._build_ui()
        self._apply_initial_settings()
        self._load_templates_list()        

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(15)
        
        # ---- OCR Engine ----
        self.input_edit = QLineEdit()
        if self.current_config.get("ocr_path"):
            self.input_edit.setPlaceholderText("Path already set")
        self.input_button = QPushButton("Browse")
        self.input_button.clicked.connect(self._browse_ocr_file)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)
        form.addRow("OCR-Engine:", input_layout)
        
        # ---- OCR Storage ----        
        self.ocr_storage_checkbox = QCheckBox("Enable OCR Storage")
        self.ocr_storage_checkbox.setToolTip("If enabled, OCR results will be stored locally.")
        self.ocr_storage_checkbox.stateChanged.connect(lambda: self._save_current_settings())
        form.addRow("Storage:", self.ocr_storage_checkbox)        
        main_layout.addLayout(form)
        
        # ---- Language Buttons ----
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.ruseng_button = QPushButton("RUS+ENG")
        self.rus_button = QPushButton("RUS")
        self.eng_button = QPushButton("ENG") 
        buttons = [self.ruseng_button, self.rus_button, self.eng_button]
        for button in buttons:
            button.setMinimumHeight(40)
            button.setCheckable(True)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            buttons_layout.addWidget(button) 
        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.ruseng_button, id=0)
        self.button_group.addButton(self.rus_button, id=1)
        self.button_group.addButton(self.eng_button, id=2)
        self.ruseng_button.setChecked(True)
        self.button_group.idClicked.connect(self._language_selected)
        
        main_layout.addWidget(QLabel("Language:"))
        main_layout.addLayout(buttons_layout)
        
        # ---- Rename templates ----
        main_layout.addSpacing(20)
        main_layout.addWidget(QLabel("Шаблоны переименования:"))
        templates_layout = QVBoxLayout()
        templates_layout.setSpacing(10)

        self.templates_list = QListWidget()
        self.templates_list.setMinimumHeight(120)
        templates_layout.addWidget(self.templates_list)

        btn_layout = QHBoxLayout()
        self.add_template_btn = QPushButton("Add")
        self.edit_template_btn = QPushButton("Edit")
        self.delete_template_btn = QPushButton("Delete")
        self.add_template_btn.clicked.connect(self._add_template)
        self.edit_template_btn.clicked.connect(self._edit_template)
        self.delete_template_btn.clicked.connect(self._delete_template)
        btn_layout.addWidget(self.add_template_btn)
        btn_layout.addWidget(self.edit_template_btn)
        btn_layout.addWidget(self.delete_template_btn)
        btn_layout.addStretch()
        templates_layout.addLayout(btn_layout)
        main_layout.addLayout(templates_layout)
        main_layout.addStretch()      
        
        main_layout.addStretch()
        
    def _apply_initial_settings(self):
        ocr_path = self.current_config.get("ocr_path", "")
        saved_lang = self.current_config.get("language", "rus+eng")
        storage_enabled = self.current_config.get("ocr_storage_enabled", False)
        
        self.input_edit.setText(ocr_path)
        self.ocr_storage_checkbox.setChecked(storage_enabled)  
        
        lang_to_id = {"rus+eng": 0, "rus": 1, "eng": 2}
        target_id = lang_to_id.get(saved_lang, 0)
        
        btn = self.button_group.button(target_id)
        if btn:
            btn.setChecked(True)

    def _browse_ocr_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select OCR Engine Executable", 
            "", 
            "Executables (*.exe)"
        )
        
        if file_path:
            self.input_edit.setText(file_path)
            self._save_current_settings()

    def _language_selected(self, id):
        self._save_current_settings()

    def _load_templates_list(self):
        self.templates_list.clear()
        templates = get_templates()
        for pattern in templates:
            self.templates_list.addItem(pattern)

    def _add_template(self):
        pattern = self._show_pattern_dialog("Add Template", "")
        if pattern is not None:
            templates = get_templates()
            templates.append(pattern)
            if save_templates(templates):
                self._load_templates_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to save template.")

    def _edit_template(self):
        current_row = self.templates_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Select a template to edit.")
            return
        templates = get_templates()
        old_pattern = templates[current_row]
        new_pattern = self._show_pattern_dialog("Edit Template", old_pattern)
        if new_pattern is not None and new_pattern != old_pattern:
            templates[current_row] = new_pattern
            if save_templates(templates):
                self._load_templates_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to edit template.")

    def _delete_template(self):
        current_row = self.templates_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Select a template to delete.")
            return
        reply = QMessageBox.question(self, "Delete", "Delete selected template?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            templates = get_templates()
            del templates[current_row]
            if save_templates(templates):
                self._load_templates_list()
                # Если удалён выбранный шаблон, сбрасываем выбор
                selected = get_selected_template_index()
                if selected == current_row or selected >= len(templates):
                    set_selected_template_index(-1)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete template.")

    def _show_pattern_dialog(self, title: str, initial: str) -> Optional[str]:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        pattern_edit = QLineEdit(initial)
        pattern_edit.setPlaceholderText("e.g. Договор №{zone0}")
        layout.addWidget(QLabel("Шаблон (используйте {zone0}, {zone1}, ...):"))
        layout.addWidget(pattern_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            text = pattern_edit.text().strip()
            if not text:
                QMessageBox.warning(self, "Error", "Pattern cannot be empty.")
                return None
            return text
        return None

    def _save_current_settings(self):
        ocr_path = self.input_edit.text().strip()
        lang_id = self.button_group.checkedId()
        ocr_storage_enabled = self.ocr_storage_checkbox.isChecked()
        
        if lang_id == -1:
            lang_id = 0
            
        lang_str = id_to_lang_string(lang_id)
        
        success = save_main_settings(ocr_path, lang_str, ocr_storage_enabled)
        
        if success:
            print(f"Settings saved to: {get_config_path()}")
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration!")        