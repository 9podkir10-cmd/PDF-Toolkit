from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QFormLayout, QMessageBox, QFileDialog,
    QPlainTextEdit
)
from pathlib import Path
from backend.structure import structure_pdfs, preview_structure

class StructurePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Структуризация PDF")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "Перемещает PDF-файлы в папки согласно шаблону из манифеста "
            "(на основе распознанного текста)."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(15)

        self.folder_edit = QLineEdit()
        self.browse_button = QPushButton("Обзор")

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.folder_edit)
        browse_layout.addWidget(self.browse_button)

        form.addRow("Папка с PDF и manifest.json:", browse_layout)
        layout.addLayout(form)

        # Панель кнопок
        button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Предпросмотр")
        self.preview_button.setMinimumHeight(40)
        self.run_button = QPushButton("Структуризировать")
        self.run_button.setMinimumHeight(40)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.run_button)
        layout.addLayout(button_layout)

        # Лог-поле для вывода дерева и результатов
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        layout.addWidget(self.log_text)

        layout.addStretch()

        # Сигналы
        self.browse_button.clicked.connect(self._browse_folder)
        self.preview_button.clicked.connect(self._preview)
        self.run_button.clicked.connect(self._run)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с PDF и manifest.json"
        )
        if directory:
            self.folder_edit.setText(directory)
            # Автоматически показываем предпросмотр при выборе папки (опционально)
            # self._preview()

    def _preview(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите папку.")
            return

        base_dir = Path(folder)
        if not base_dir.exists():
            QMessageBox.warning(self, "Ошибка", "Папка не существует.")
            return

        self.log_text.clear()
        self.log_text.appendPlainText("Сканирование структуры...")
        try:
            tree_str = preview_structure(base_dir)
            self.log_text.appendPlainText(tree_str)
        except Exception as e:
            self.log_text.appendPlainText(f"Ошибка: {str(e)}")

    def _run(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите папку.")
            return

        base_dir = Path(folder)
        if not base_dir.exists():
            QMessageBox.warning(self, "Ошибка", "Папка не существует.")
            return

        # Сначала показываем предпросмотр, если он ещё не отображался
        self._preview()

        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Выполнить структуризацию согласно показанному дереву?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.log_text.appendPlainText("\nНачинаем структуризацию...")
        self.run_button.setEnabled(False)
        self.preview_button.setEnabled(False)

        try:
            result = structure_pdfs(base_dir)
            if "error" in result:
                QMessageBox.critical(self, "Ошибка", result["error"])
                self.log_text.appendPlainText(f"Ошибка: {result['error']}")
            else:
                self.log_text.appendPlainText(f"Перемещено файлов: {result['moved']}")
                self.log_text.appendPlainText(f"Ошибок: {result['errors']}")
                for detail in result.get('details', []):
                    self.log_text.appendPlainText(detail)
                QMessageBox.information(
                    self,
                    "Готово",
                    f"Структуризация завершена.\nПеремещено: {result['moved']}\nОшибок: {result['errors']}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            self.log_text.appendPlainText(f"Исключение: {str(e)}")
        finally:
            self.run_button.setEnabled(True)
            self.preview_button.setEnabled(True)