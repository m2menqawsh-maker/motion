"""
scripts/core/storage/storage_service.py — Unified Heavy Object Storage Abstraction (S24.5 - ADR-003).

Provides:
- Abstract base StorageService
- LocalStorageBackend for development, hermetic testing, and local runners
- S3CompatibleStorageBackend for production SaaS object storage (AWS S3, MinIO, R2, Ceph)
- Server-generated canonical storage keys
- Fail-closed path traversal validation and boundary confinement
"""

from __future__ import annotations

import io
import os
import re
import shutil
import hmac
import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when an object key does not exist."""
    pass


class StorageSecurityError(StorageError):
    """Raised on illegal traversal, illegal character, or escape attempts."""
    pass


class StorageMetadata(BaseModel):
    """Metadata describing a stored object."""
    key: str
    size_bytes: int
    content_type: str = "application/octet-stream"
    sha256: Optional[str] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


SAFE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\/]+$")


def validate_storage_key(key: str) -> str:
    """
    Validates that a storage key is well-formed and does not attempt directory traversal.
    Fails closed on any traversal, absolute paths, or forbidden characters.
    """
    if not key or not isinstance(key, str):
        raise StorageSecurityError("Storage key must be a non-empty string.")

    if key.startswith("/"):
        raise StorageSecurityError(f"Storage key cannot start with a slash (absolute path forbidden): '{key}'")

    normalized = key.strip()

    if not normalized:
        raise StorageSecurityError("Storage key cannot be empty or root.")

    # Check for path traversal segments
    parts = normalized.split("/")
    for p in parts:
        if p in ("", ".", ".."):
            raise StorageSecurityError(f"Invalid path segment in storage key '{key}': '{p}'")

    if not SAFE_KEY_PATTERN.match(normalized):
        raise StorageSecurityError(f"Storage key contains illegal characters: '{key}'")

    return normalized


def build_storage_key(
    workspace_id: str,
    project_id: str,
    category: str,
    item_id: str,
    filename: str,
) -> str:
    """
    Constructs an authoritative, server-generated canonical storage key.
    
    Format:
      workspaces/{workspace_id}/projects/{project_id}/{category}/{item_id}/{filename}
    """
    for arg, name in [
        (workspace_id, "workspace_id"),
        (project_id, "project_id"),
        (category, "category"),
        (item_id, "item_id"),
        (filename, "filename"),
    ]:
        if not arg or ".." in arg or "/" in arg or "\\" in arg:
            raise StorageSecurityError(f"Invalid {name} for storage key: '{arg}'")

    raw_key = f"workspaces/{workspace_id}/projects/{project_id}/{category}/{item_id}/{filename}"
    return validate_storage_key(raw_key)


class StorageService(ABC):
    """Abstract canonical interface for heavy/binary object persistence."""

    @abstractmethod
    def put(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> StorageMetadata:
        """Stores object bytes at key."""
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieves entire object bytes."""
        pass

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Opens a readable stream for the object."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Checks if key exists."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Deletes object. Returns True if deleted, False if did not exist."""
        pass

    @abstractmethod
    def copy(self, src_key: str, dst_key: str) -> StorageMetadata:
        """Copies an object from src_key to dst_key."""
        pass

    @abstractmethod
    def metadata(self, key: str) -> StorageMetadata:
        """Retrieves metadata for key without fetching full content."""
        pass

    @abstractmethod
    def signed_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        """Generates a secure, time-bounded URL for reading/downloading."""
        pass

    def download_to_file(self, key: str, target_path: Path) -> Path:
        """Materializes stored object bytes to target local file."""
        data = self.get(key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(data)
        return target_path


class LocalStorageBackend(StorageService):
    """
    Filesystem-backed StorageService confined strictly to a designated root.
    Used for hermetic local testing, development, and standalone single-host setups.
    """

    def __init__(self, root_dir: Union[Path, str], secret_key: Optional[str] = None):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.secret_key = secret_key or "local-storage-dev-secret-minimum-32-chars-long!"

    def _resolve_path(self, key: str) -> Path:
        clean_key = validate_storage_key(key)
        target = (self.root_dir / clean_key).resolve()
        # Enforce strict confinement inside root_dir
        if not str(target).startswith(str(self.root_dir)):
            raise StorageSecurityError(f"Storage path traversal detected: key '{key}' escapes root.")
        return target

    def put(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> StorageMetadata:
        target = self._resolve_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            payload = data
        else:
            payload = data.read()

        sha256 = hashlib.sha256(payload).hexdigest()

        # Atomic write via temp file
        tmp = target.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

        stat = target.stat()
        return StorageMetadata(
            key=validate_storage_key(key),
            size_bytes=stat.st_size,
            content_type=content_type,
            sha256=sha256,
            last_modified=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
            etag=f'"{sha256}"',
        )

    def get(self, key: str) -> bytes:
        target = self._resolve_path(key)
        if not target.exists() or not target.is_file():
            raise StorageNotFoundError(f"Object not found: '{key}'")
        return target.read_bytes()

    def open(self, key: str) -> BinaryIO:
        target = self._resolve_path(key)
        if not target.exists() or not target.is_file():
            raise StorageNotFoundError(f"Object not found: '{key}'")
        return open(target, "rb")

    def exists(self, key: str) -> bool:
        try:
            target = self._resolve_path(key)
            return target.exists() and target.is_file()
        except StorageSecurityError:
            return False

    def delete(self, key: str) -> bool:
        target = self._resolve_path(key)
        if target.exists() and target.is_file():
            try:
                target.unlink()
                return True
            except OSError:
                return False
        return False

    def copy(self, src_key: str, dst_key: str) -> StorageMetadata:
        data = self.get(src_key)
        meta = self.metadata(src_key)
        return self.put(dst_key, data, content_type=meta.content_type)

    def metadata(self, key: str) -> StorageMetadata:
        target = self._resolve_path(key)
        if not target.exists() or not target.is_file():
            raise StorageNotFoundError(f"Object not found: '{key}'")
        stat = target.stat()
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        return StorageMetadata(
            key=validate_storage_key(key),
            size_bytes=stat.st_size,
            content_type="application/octet-stream",
            sha256=sha,
            last_modified=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
            etag=f'"{sha}"',
        )

    def signed_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        clean_key = validate_storage_key(key)
        if not self.exists(clean_key):
            raise StorageNotFoundError(f"Cannot generate signed URL for non-existent key: '{key}'")
        expires_at = int(time.time()) + expires_in_seconds
        sig_payload = f"{clean_key}:{expires_at}".encode("utf-8")
        signature = hmac.new(self.secret_key.encode("utf-8"), sig_payload, hashlib.sha256).hexdigest()
        return f"/api/storage/download?key={clean_key}&expires={expires_at}&signature={signature}"

    def download_to_file(self, key: str, target_path: Path) -> Path:
        src = self._resolve_path(key)
        if not src.exists():
            raise StorageNotFoundError(f"Object not found: '{key}'")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != target_path.resolve():
            shutil.copyfile(src, target_path)
        return target_path


class S3CompatibleStorageBackend(StorageService):
    """
    S3 and S3-compatible Object Storage implementation using boto3.
    Operates against AWS S3, Cloudflare R2, MinIO, or Ceph.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name

        if client is not None:
            self._client = client
        else:
            import boto3
            session_kwargs: Dict[str, Any] = {"region_name": region_name}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs["aws_access_key_id"] = aws_access_key_id
                session_kwargs["aws_secret_access_key"] = aws_secret_access_key

            client_kwargs: Dict[str, Any] = {}
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url

            self._client = boto3.client("s3", **session_kwargs, **client_kwargs)

    def put(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> StorageMetadata:
        clean_key = validate_storage_key(key)
        body = data if isinstance(data, (bytes, bytearray)) else data.read()
        sha256 = hashlib.sha256(body).hexdigest()

        from botocore.exceptions import ClientError
        try:
            resp = self._client.put_object(
                Bucket=self.bucket_name,
                Key=clean_key,
                Body=body,
                ContentType=content_type,
            )
            etag = resp.get("ETag", "").strip('"')
            return StorageMetadata(
                key=clean_key,
                size_bytes=len(body),
                content_type=content_type,
                sha256=sha256,
                etag=etag,
            )
        except ClientError as e:
            raise StorageError(f"S3 put_object failed for '{clean_key}': {e}")

    def get(self, key: str) -> bytes:
        clean_key = validate_storage_key(key)
        from botocore.exceptions import ClientError
        try:
            resp = self._client.get_object(Bucket=self.bucket_name, Key=clean_key)
            return resp["Body"].read()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise StorageNotFoundError(f"S3 object not found: '{clean_key}'")
            raise StorageError(f"S3 get_object failed: {e}")

    def open(self, key: str) -> BinaryIO:
        data = self.get(key)
        return io.BytesIO(data)

    def exists(self, key: str) -> bool:
        clean_key = validate_storage_key(key)
        from botocore.exceptions import ClientError
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                return False
            return False

    def delete(self, key: str) -> bool:
        clean_key = validate_storage_key(key)
        from botocore.exceptions import ClientError
        try:
            if not self.exists(clean_key):
                return False
            self._client.delete_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except ClientError:
            return False

    def copy(self, src_key: str, dst_key: str) -> StorageMetadata:
        clean_src = validate_storage_key(src_key)
        clean_dst = validate_storage_key(dst_key)
        from botocore.exceptions import ClientError
        try:
            self._client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": clean_src},
                Key=clean_dst,
            )
            return self.metadata(clean_dst)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise StorageNotFoundError(f"S3 source object not found: '{clean_src}'")
            raise StorageError(f"S3 copy_object failed: {e}")

    def metadata(self, key: str) -> StorageMetadata:
        clean_key = validate_storage_key(key)
        from botocore.exceptions import ClientError
        try:
            resp = self._client.head_object(Bucket=self.bucket_name, Key=clean_key)
            etag = resp.get("ETag", "").strip('"')
            return StorageMetadata(
                key=clean_key,
                size_bytes=resp.get("ContentLength", 0),
                content_type=resp.get("ContentType", "application/octet-stream"),
                etag=etag,
                last_modified=str(resp.get("LastModified", "")),
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise StorageNotFoundError(f"S3 object not found: '{clean_key}'")
            raise StorageError(f"S3 head_object failed: {e}")

    def signed_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        clean_key = validate_storage_key(key)
        from botocore.exceptions import ClientError
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": clean_key},
                ExpiresIn=expires_in_seconds,
            )
            return url
        except ClientError as e:
            raise StorageError(f"Failed to generate S3 presigned URL: {e}")


_default_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Factory function returning the singleton active StorageService
    according to environment settings.
    """
    global _default_storage_service
    if _default_storage_service is not None:
        return _default_storage_service

    from api.core.config import get_api_settings
    settings = get_api_settings()

    if settings.storage_backend in ("s3", "s3-compatible", "minio"):
        _default_storage_service = S3CompatibleStorageBackend(
            bucket_name=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
    else:
        _default_storage_service = LocalStorageBackend(root_dir=settings.storage_local_root)

    return _default_storage_service


def set_storage_service(service: Optional[StorageService]) -> None:
    """Explicitly override storage service singleton (primarily for tests)."""
    global _default_storage_service
    _default_storage_service = service
