from .pdf_viewer import BasePDFViewer, BasePDFGraphicsView

class ReadGraphicsView(BasePDFGraphicsView):
    pass

class ReadViewer(BasePDFViewer):
    def _create_view(self):
        return ReadGraphicsView(self)