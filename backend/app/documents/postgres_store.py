from typing import Callable

from backend.app.documents.models import DocumentRecord


class PostgresDocumentMetadataStore:
    def __init__(
        self,
        *,
        database_url: str,
        connection_factory: Callable[[], object] | None = None,
    ) -> None:
        self._database_url = database_url
        self._connection_factory = connection_factory or self._create_connection
        self._ensure_schema()

    def record_document(self, record: DocumentRecord) -> None:
        params = record.model_dump(mode="python")
        with self._connection_factory() as connection:
            connection.execute(
                """
                INSERT INTO document_metadata (
                    document_id,
                    workspace_id,
                    workspace_name,
                    uploaded_by_employee_id,
                    security_level,
                    filename,
                    parser,
                    character_count,
                    text_preview,
                    storage_key,
                    indexing_job_id,
                    indexing_status,
                    indexing_error,
                    chunk_count,
                    uploaded_at
                )
                VALUES (
                    %(document_id)s,
                    %(workspace_id)s,
                    %(workspace_name)s,
                    %(uploaded_by_employee_id)s,
                    %(security_level)s,
                    %(filename)s,
                    %(parser)s,
                    %(character_count)s,
                    %(text_preview)s,
                    %(storage_key)s,
                    %(indexing_job_id)s,
                    %(indexing_status)s,
                    %(indexing_error)s,
                    %(chunk_count)s,
                    %(uploaded_at)s
                )
                ON CONFLICT (document_id) DO UPDATE SET
                    workspace_name = EXCLUDED.workspace_name,
                    uploaded_by_employee_id = EXCLUDED.uploaded_by_employee_id,
                    security_level = EXCLUDED.security_level,
                    filename = EXCLUDED.filename,
                    parser = EXCLUDED.parser,
                    character_count = EXCLUDED.character_count,
                    text_preview = EXCLUDED.text_preview,
                    storage_key = EXCLUDED.storage_key,
                    indexing_job_id = EXCLUDED.indexing_job_id,
                    indexing_status = EXCLUDED.indexing_status,
                    indexing_error = EXCLUDED.indexing_error,
                    chunk_count = EXCLUDED.chunk_count,
                    uploaded_at = EXCLUDED.uploaded_at
                """,
                params,
            )
            connection.commit()

    def list_documents(
        self,
        *,
        workspace_id: str,
        limit: int = 100,
    ) -> list[DocumentRecord]:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                SELECT
                    document_id,
                    workspace_id,
                    workspace_name,
                    uploaded_by_employee_id,
                    security_level,
                    filename,
                    parser,
                    character_count,
                    text_preview,
                    storage_key,
                    indexing_job_id,
                    indexing_status,
                    indexing_error,
                    chunk_count,
                    uploaded_at
                FROM document_metadata
                WHERE workspace_id = %(workspace_id)s
                ORDER BY uploaded_at DESC
                LIMIT %(limit)s
                """,
                {"workspace_id": workspace_id, "limit": limit},
            )
            rows = cursor.fetchall()

        return [DocumentRecord.model_validate(row) for row in rows]

    def get_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                f"""
                SELECT
                    {_document_columns()}
                FROM document_metadata
                WHERE workspace_id = %(workspace_id)s
                AND document_id = %(document_id)s
                """,
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                },
            )
            rows = cursor.fetchall()

        if not rows:
            return None
        return DocumentRecord.model_validate(rows[0])

    def delete_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> DocumentRecord | None:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                f"""
                DELETE FROM document_metadata
                WHERE workspace_id = %(workspace_id)s
                AND document_id = %(document_id)s
                RETURNING
                    {_document_columns()}
                """,
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                },
            )
            rows = cursor.fetchall()
            connection.commit()

        if not rows:
            return None
        return DocumentRecord.model_validate(rows[0])

    def _ensure_schema(self) -> None:
        with self._connection_factory() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_metadata (
                    document_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    workspace_name TEXT NOT NULL,
                    uploaded_by_employee_id TEXT,
                    security_level TEXT NOT NULL DEFAULT 'internal',
                    filename TEXT NOT NULL,
                    parser TEXT NOT NULL,
                    character_count INTEGER NOT NULL,
                    text_preview TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    indexing_job_id TEXT NOT NULL,
                    indexing_status TEXT NOT NULL,
                    indexing_error TEXT,
                    chunk_count INTEGER NOT NULL,
                    uploaded_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                """
                ALTER TABLE document_metadata
                ADD COLUMN IF NOT EXISTS indexing_error TEXT
                """
            )
            connection.execute(
                """
                ALTER TABLE document_metadata
                ADD COLUMN IF NOT EXISTS uploaded_by_employee_id TEXT
                """
            )
            connection.execute(
                """
                ALTER TABLE document_metadata
                ADD COLUMN IF NOT EXISTS security_level TEXT NOT NULL DEFAULT 'internal'
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_document_metadata_workspace_uploaded_at
                ON document_metadata (workspace_id, uploaded_at DESC)
                """
            )
            connection.commit()

    def _create_connection(self) -> object:
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)


def _document_columns() -> str:
    return """
                    document_id,
                    workspace_id,
                    workspace_name,
                    uploaded_by_employee_id,
                    security_level,
                    filename,
                    parser,
                    character_count,
                    text_preview,
                    storage_key,
                    indexing_job_id,
                    indexing_status,
                    indexing_error,
                    chunk_count,
                    uploaded_at
    """
