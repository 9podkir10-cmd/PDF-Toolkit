import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def run_gui() -> None:
    app = QApplication(sys.argv)

    app.setApplicationName("PDF-Toolkit")
    app.setOrganizationName("PDF-Toolkit")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())