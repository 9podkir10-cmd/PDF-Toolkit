from typing import List, Optional
from backend.scanning.models import Page, Document, Batch

class BatchManager:
    @staticmethod
    def create_batch_from_pages(pages: List[Page], split_by_count: Optional[int] = None) -> Batch:
        """
        Создает Batch из списка страниц.
        Если split_by_count указан, группирует страницы в документы по этому числу.
        """
        batch = Batch(name="Batch_1")
        if not pages:
            return batch

        if split_by_count and split_by_count > 0:
            # Группируем страницы в документы
            for i in range(0, len(pages), split_by_count):
                chunk = pages[i:i + split_by_count]
                doc = Document(pages=chunk)
                batch.documents.append(doc)
        else:
            # Все страницы в одном документе
            batch.documents.append(Document(pages=pages))
        return batch