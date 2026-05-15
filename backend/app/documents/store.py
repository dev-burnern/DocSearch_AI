from threading import Lock
from typing import Protocol

from backend.app.documents.models import DocumentRecord


class DocumentMetadataStore(Protocol):
    def record_document(self, record: DocumentRecord) -> None:
        raise NotImplementedError

    def get_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
        raise NotImplementedError

    def delete_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
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
            self._records = [
                current
                for current in self._records
                if not (
                    current.workspace_id == record.workspace_id
                    and current.document_id == record.document_id
                )
            ]
            self._records.append(record)

    def get_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
        with self._lock:
            return next(
                (
                    record
                    for record in self._records
                    if record.workspace_id == workspace_id
                    and record.document_id == document_id
                ),
                None,
            )

    def delete_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
        with self._lock:
            deleted = next(
                (
                    record
                    for record in self._records
                    if record.workspace_id == workspace_id
                    and record.document_id == document_id
                ),
                None,
            )
            if deleted is None:
                return None

            self._records = [
                record
                for record in self._records
                if not (
                    record.workspace_id == workspace_id
                    and record.document_id == document_id
                )
            ]

        return deleted

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
