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
from gui.signals import app_signals
from backend.config import (
    load_config,
    save_main_settings,
    id_to_lang_string,
    get_config_path,
    get_templates,
    save_templates,
    set_selected_template_index,
    get_selected_template_index,
    get_scan_profiles,   
    save_scan_profiles,       
    get_default_scan_profile, 
    set_default_scan_profile, 
)

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_config = load_config()
        self._build_ui()
        self._apply_initial_settings()
        self._load_templates_list() 
        self._load_profiles_list()
        self.add_profile_btn.clicked.connect(self._add_profile)
        self.edit_profile_btn.clicked.connect(self._edit_profile)
        self.delete_profile_btn.clicked.connect(self._delete_profile)       

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
        
        # ---- Scan profiles ----
        main_layout.addSpacing(20)
        main_layout.addWidget(QLabel("Профили сканирования:"))

        profiles_layout = QVBoxLayout()
        profiles_layout.setSpacing(10)

        self.profiles_list = QListWidget()
        self.profiles_list.setMinimumHeight(120)
        profiles_layout.addWidget(self.profiles_list)

        btn_layout_profiles = QHBoxLayout()
        self.add_profile_btn = QPushButton("Add")
        self.edit_profile_btn = QPushButton("Edit")
        self.delete_profile_btn = QPushButton("Delete")
        btn_layout_profiles.addWidget(self.add_profile_btn)
        btn_layout_profiles.addWidget(self.edit_profile_btn)
        btn_layout_profiles.addWidget(self.delete_profile_btn)
        btn_layout_profiles.addStretch()
        profiles_layout.addLayout(btn_layout_profiles)
        main_layout.addLayout(profiles_layout)
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
                app_signals.templates_changed.emit() 
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
                app_signals.templates_changed.emit() 
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
                app_signals.templates_changed.emit() 
                selected = get_selected_template_index()
                if selected == current_row or selected >= len(templates):
                    set_selected_template_index(-1)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete template.")

    def _show_pattern_dialog(self, title: str, initial: str) -> Optional[str]:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)     
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

    def _load_profiles_list(self):
        self.profiles_list.clear()
        profiles = get_scan_profiles()
        for profile in profiles:
            name = profile.get("name", "Без имени")
            self.profiles_list.addItem(name)

    def _add_profile(self):
        profile_data = self._show_profile_dialog("Добавить профиль", None)
        if profile_data is not None:
            profiles = get_scan_profiles()
            if any(p.get("name") == profile_data["name"] for p in profiles):
                QMessageBox.warning(self, "Ошибка", "Профиль с таким именем уже существует.")
                return
            profiles.append(profile_data)
            if save_scan_profiles(profiles):
                self._load_profiles_list()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить профиль.")

    def _edit_profile(self):
        current_row = self.profiles_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите профиль для редактирования.")
            return
        profiles = get_scan_profiles()
        old_profile = profiles[current_row]
        new_profile = self._show_profile_dialog("Редактировать профиль", old_profile)
        if new_profile is not None and new_profile != old_profile:
            if new_profile["name"] != old_profile["name"]:
                if any(p.get("name") == new_profile["name"] for p in profiles if p != old_profile):
                    QMessageBox.warning(self, "Ошибка", "Профиль с таким именем уже существует.")
                    return
            profiles[current_row] = new_profile
            if save_scan_profiles(profiles):
                self._load_profiles_list()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изменения.")

    def _delete_profile(self):
        current_row = self.profiles_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите профиль для удаления.")
            return
        reply = QMessageBox.question(self, "Удаление", "Удалить выбранный профиль?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            profiles = get_scan_profiles()
            del profiles[current_row]
            if save_scan_profiles(profiles):
                self._load_profiles_list()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить профиль.")

    def _show_profile_dialog(self, title: str, initial_profile: Optional[dict]) -> Optional[dict]:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox, QComboBox, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        # Имя профиля
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название профиля")
        layout.addWidget(QLabel("Имя:"))
        layout.addWidget(name_edit)

        # Разрешение (DPI)
        dpi_spin = QSpinBox()
        dpi_spin.setRange(50, 1200)
        dpi_spin.setValue(300)
        layout.addWidget(QLabel("Разрешение (DPI):"))
        layout.addWidget(dpi_spin)

        # Цветовой режим
        color_combo = QComboBox()
        color_combo.addItems(["Цветной", "Оттенки серого", "Черно-белый"])
        layout.addWidget(QLabel("Цветовой режим:"))
        layout.addWidget(color_combo)

        # Размер страницы
        size_combo = QComboBox()
        size_combo.addItems(["A4", "A5", "Letter", "Legal"])
        layout.addWidget(QLabel("Размер страницы:"))
        layout.addWidget(size_combo)

        # Формат файла
        format_combo = QComboBox()
        format_combo.addItems(["PDF", "JPEG", "PNG"])
        layout.addWidget(QLabel("Формат файла:"))
        layout.addWidget(format_combo)

        # Яркость и контрастность (опционально)
        brightness_spin = QSpinBox()
        brightness_spin.setRange(-100, 100)
        brightness_spin.setValue(0)
        layout.addWidget(QLabel("Яркость:"))
        layout.addWidget(brightness_spin)

        contrast_spin = QSpinBox()
        contrast_spin.setRange(-100, 100)
        contrast_spin.setValue(0)
        layout.addWidget(QLabel("Контрастность:"))
        layout.addWidget(contrast_spin)

        # Если редактируем – заполняем поля
        if initial_profile:
            name_edit.setText(initial_profile.get("name", ""))
            dpi_spin.setValue(initial_profile.get("dpi", 300))
            color_map = {"color": 0, "gray": 1, "bw": 2}
            color_combo.setCurrentIndex(color_map.get(initial_profile.get("color_mode", "color"), 0))
            size_combo.setCurrentText(initial_profile.get("page_size", "A4"))
            format_combo.setCurrentText(initial_profile.get("file_format", "PDF"))
            brightness_spin.setValue(initial_profile.get("brightness", 0))
            contrast_spin.setValue(initial_profile.get("contrast", 0))

        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Имя профиля не может быть пустым.")
                return None

            # Преобразуем выбранный цветовой режим в строковое значение для хранения
            color_text = color_combo.currentText()
            if color_text == "Цветной":
                color_mode = "color"
            elif color_text == "Оттенки серого":
                color_mode = "gray"
            else:
                color_mode = "bw"

            return {
                "name": name,
                "dpi": dpi_spin.value(),
                "color_mode": color_mode,
                "page_size": size_combo.currentText(),
                "file_format": format_combo.currentText().lower(),  # pdf, jpeg, png
                "brightness": brightness_spin.value(),
                "contrast": contrast_spin.value(),
            }
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