from PySide6.QtCore import QObject, Signal

class AppSignals(QObject):
    templates_changed = Signal()
    dashboard_updated = Signal() 
app_signals = AppSignals()