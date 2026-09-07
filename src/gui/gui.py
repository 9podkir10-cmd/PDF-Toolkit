import sys, os, ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from .main_window import MainWindow

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_gui() -> None:
    app_id = "9podkir10-cmd.PDF-Toolkit"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)
    app.setApplicationName("PDF-Toolkit")
    app.setOrganizationName("PDF-Toolkit")

    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Предупреждение: иконка не найдена по пути {icon_path}")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())