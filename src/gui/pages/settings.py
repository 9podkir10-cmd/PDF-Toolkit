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
)
from backend.config import load_config, save_config, id_to_lang_string, get_config_path

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_config = load_config()
        self._build_ui()
        self._apply_initial_settings()

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

        self.input_edit = QLineEdit()
        if self.current_config.get("ocr_path"):
            self.input_edit.setPlaceholderText("Path already set")
        
        self.input_button = QPushButton("Browse")
        self.input_button.clicked.connect(self._browse_ocr_file)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_button)

        form.addRow("OCR-Engine:", input_layout)

        main_layout.addLayout(form)

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
        main_layout.addStretch()
        
    def _apply_initial_settings(self):
        ocr_path = self.current_config.get("ocr_path", "")
        saved_lang = self.current_config.get("language", "ruseng")
        
        self.input_edit.setText(ocr_path)
        
        lang_to_id = {"ruseng": 0, "rus": 1, "eng": 2}
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

    def _save_current_settings(self):
        ocr_path = self.input_edit.text().strip()
        lang_id = self.button_group.checkedId()
        
        if lang_id == -1:
            lang_id = 0
            
        lang_str = id_to_lang_string(lang_id)
        
        success = save_config(ocr_path, lang_str)
        
        if success:
            print(f"Settings saved to: {get_config_path()}")
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration!")        