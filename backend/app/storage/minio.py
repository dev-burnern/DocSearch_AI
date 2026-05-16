from io import BytesIO
from typing import Protocol

from minio import Minio

from backend.app.core.config import Settings, get_settings


class StorageService(Protocol):
    def upload_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> str:
        ...

    def download_document(self, *, storage_key: str) -> bytes:
        ...

    def delete_document(self, *, storage_key: str) -> None:
        ...


class MinioStorageService:
    def __init__(self, settings: Settings, client: Minio | None = None) -> None:
        self._bucket = settings.minio_bucket
        self._client = client or Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket()

    def upload_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> str:
        storage_key = f"{workspace_id}/{document_id}/{filename}"
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=storage_key,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )
        return storage_key

    def download_document(self, *, storage_key: str) -> bytes:
        response = self._client.get_object(
            bucket_name=self._bucket,
            object_name=storage_key,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_document(self, *, storage_key: str) -> None:
        self._client.remove_object(
            bucket_name=self._bucket,
            object_name=storage_key,
        )

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)


def create_minio_storage_service() -> MinioStorageService:
    return MinioStorageService(get_settings())
