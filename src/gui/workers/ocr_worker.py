from PySide6.QtCore import QObject, Signal, Slot

class OCRWorker(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, ocr_workflow, pdf_path, regions, dpi=300):
        super().__init__()
        self.ocr_workflow = ocr_workflow
        self.pdf_path = pdf_path
        self.regions = regions
        self.dpi = dpi
        self._cancel_requested = False

    @Slot()
    def cancel(self):
        self._cancel_requested = True

    @Slot()
    def run(self):
        try:
            # можно добавить
            # result = self.ocr_workflow.recognize_zones(
            #     self.pdf_path, self.regions, self.dpi,
            #     cancel_check=lambda: self._cancel_requested
            # )
            # Но пока без cancel.
            result = self.ocr_workflow.recognize_zones(
                self.pdf_path,
                self.regions,
                self.dpi
            )
            if self._cancel_requested:
                self.finished.emit(None)
            else:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))