from threading import Lock
from typing import Protocol

from backend.app.documents.models import DocumentRecord


class DocumentMetadataStore(Protocol):
    def record_document(self, record: DocumentRecord) -> None:
        raise NotImplementedError

    def list_documents(
        self,
        *,
        workspace_id: str,
        limit: int = 100,
    ) -> list[DocumentRecord]:
        raise NotImplementedError


class InMemoryDocumentMetadataStore:
    def __init__(self) -> None:
        self._records: list[DocumentRecord] = []
        self._lock = Lock()

    def record_document(self, record: DocumentRecord) -> None:
        with self._lock:
            self._records.append(record)

    def list_documents(
        self,
        *,
        workspace_id: str,
        limit: int = 100,
    ) -> list[DocumentRecord]:
        with self._lock:
            records = [
                record
                for record in self._records
                if record.workspace_id == workspace_id
            ]

        return sorted(
            records,
            key=lambda record: record.uploaded_at,
            reverse=True,
        )[:limit]
