import sys, os, ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from .main_window import MainWindow

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.abspath(os.path.join(current_dir, ".."))
        
    return os.path.join(base_path, relative_path)

def load_stylesheet(app, filename):
    style_path = get_resource_path(filename)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"⚠️ Предупреждение: Файл стилей не найден по пути {style_path}")

def run_gui() -> None:
    app_id = "9podkir10-cmd.PDF-Toolkit"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        
    app.setApplicationName("PDF-Toolkit")
    app.setOrganizationName("PDF-Toolkit")

    load_stylesheet(app, "assets/styles/style.qss")
    icon_path = get_resource_path("assets/icon.ico")
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Предупреждение: иконка не найдена по пути {icon_path}")

    window = MainWindow()
    window.showMaximized()
    app.exec()