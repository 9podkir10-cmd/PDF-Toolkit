from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox, QGridLayout
)
from gui.signals import app_signals
from backend.dashboard_b import get_dashboard_stats

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_folder = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Dashboard — Статистика индексации")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Выбор папки
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Папка не выбрана")
        self.folder_label.setStyleSheet("font-weight: bold;")
        self.select_btn = QPushButton("Выбрать папку...")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.select_btn)
        folder_layout.addStretch()
        layout.addLayout(folder_layout)

        # Группа со статистикой
        stats_group = QGroupBox("Статистика")
        grid = QGridLayout()
        self.total_label = QLabel("0")
        self.recognized_label = QLabel("0")
        self.remaining_label = QLabel("0")
        self.percent_label = QLabel("0%")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        grid.addWidget(QLabel("Всего PDF:"), 0, 0)
        grid.addWidget(self.total_label, 0, 1)
        grid.addWidget(QLabel("Распознано:"), 1, 0)
        grid.addWidget(self.recognized_label, 1, 1)
        grid.addWidget(QLabel("Осталось:"), 2, 0)
        grid.addWidget(self.remaining_label, 2, 1)
        grid.addWidget(QLabel("Прогресс:"), 3, 0)
        grid.addWidget(self.progress_bar, 3, 1)
        grid.addWidget(self.percent_label, 3, 2)
        stats_group.setLayout(grid)
        layout.addWidget(stats_group)

        # (Опционально) таблица/список файлов – можно добавить позже
        layout.addStretch()

        # Установим начальное состояние
        self._update_stats(None)

    def _connect_signals(self):
        self.select_btn.clicked.connect(self._select_folder)
        app_signals.dashboard_updated.connect(self._refresh_current)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с PDF и manifest.json")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self._update_stats(folder)

    def _refresh_current(self):
        if self.current_folder and Path(self.current_folder).exists():
            self._update_stats(self.current_folder)

    def _update_stats(self, folder_path):
        if not folder_path or not Path(folder_path).exists():
            self.total_label.setText("0")
            self.recognized_label.setText("0")
            self.remaining_label.setText("0")
            self.percent_label.setText("0%")
            self.progress_bar.setValue(0)
            return

        stats = get_dashboard_stats(folder_path)
        if "error" in stats:
            QMessageBox.warning(self, "Ошибка", stats["error"])
            return

        self.total_label.setText(str(stats["total"]))
        self.recognized_label.setText(str(stats["recognized"]))
        self.remaining_label.setText(str(stats["remaining"]))
        self.percent_label.setText(f"{stats['percent']:.1f}%")
        self.progress_bar.setValue(int(stats["percent"]))

        # Если нет манифеста, можно показать предупреждение
        if not stats.get("has_manifest", True):
            self.folder_label.setText(f"{folder_path} (нет manifest.json)")