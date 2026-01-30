"""
Object Storage Service (MinIO)
파일 저장소 서비스
"""
from __future__ import annotations

import io
import uuid
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    """MinIO object storage service"""
    
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()
    
    def _ensure_bucket(self) -> None:
        """Ensure the bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            if "BucketAlreadyOwnedByYou" not in str(e):
                raise
    
    def upload_file(
        self,
        file_data: BinaryIO | bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> str:
        """
        Upload a file to storage
        Returns the object name (storage key)
        """
        if isinstance(file_data, bytes):
            file_data = io.BytesIO(file_data)
            file_data.seek(0, 2)  # Seek to end
            size = file_data.tell()
            file_data.seek(0)  # Seek back to start
        else:
            # Get size by seeking
            file_data.seek(0, 2)
            size = file_data.tell()
            file_data.seek(0)
        
        self.client.put_object(
            self.bucket,
            object_name,
            file_data,
            size,
            content_type=content_type,
            metadata=metadata or {},
        )
        
        return object_name
    
    def upload_document(
        self,
        file_data: BinaryIO | bytes,
        document_id: uuid.UUID,
        filename: str,
        version: int = 1,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a document with proper path structure
        Returns the storage key
        """
        # Structure: originals/{document_id}/v{version}/{filename}
        object_name = f"originals/{document_id}/v{version}/{filename}"
        return self.upload_file(file_data, object_name, content_type)
    
    def upload_thumbnail(
        self,
        image_data: bytes,
        document_id: uuid.UUID,
        page_number: int,
    ) -> str:
        """Upload a page thumbnail"""
        object_name = f"thumbnails/{document_id}/page_{page_number:04d}.png"
        return self.upload_file(image_data, object_name, "image/png")
    
    def download_file(self, object_name: str) -> bytes:
        """Download a file from storage"""
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        finally:
            response.close()
            response.release_conn()
    
    def get_file_stream(self, object_name: str) -> BinaryIO:
        """Get a file stream (for large files)"""
        return self.client.get_object(self.bucket, object_name)
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """Get a presigned URL for temporary access"""
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            expires=expires,
        )
    
    def delete_file(self, object_name: str) -> None:
        """Delete a file from storage"""
        self.client.remove_object(self.bucket, object_name)
    
    def delete_document(self, document_id: uuid.UUID) -> None:
        """Delete all files for a document"""
        # Delete originals
        self._delete_prefix(f"originals/{document_id}/")
        # Delete thumbnails
        self._delete_prefix(f"thumbnails/{document_id}/")
        # Delete extracted
        self._delete_prefix(f"extracted/{document_id}/")
    
    def _delete_prefix(self, prefix: str) -> None:
        """Delete all objects with a given prefix"""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        for obj in objects:
            self.client.remove_object(self.bucket, obj.object_name)
    
    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists"""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False
    
    def get_file_info(self, object_name: str) -> dict | None:
        """Get file metadata"""
        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "metadata": stat.metadata,
            }
        except S3Error:
            return None
    
    def list_documents(self, document_id: uuid.UUID) -> list[dict]:
        """List all files for a document"""
        files = []
        prefix = f"originals/{document_id}/"
        
        for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True):
            files.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
            })
        
        return files


# Singleton instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get storage service singleton"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
