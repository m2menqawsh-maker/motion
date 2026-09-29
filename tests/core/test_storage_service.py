"""
tests/core/test_storage_service.py — Unit Tests for StorageService Abstraction (S24.5).
"""

import io
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from scripts.core.storage import (
    LocalStorageBackend,
    S3CompatibleStorageBackend,
    StorageNotFoundError,
    StorageSecurityError,
    validate_storage_key,
    build_storage_key,
)


def test_build_and_validate_storage_key():
    key = build_storage_key(
        workspace_id="ws_123",
        project_id="prj_456",
        category="assets",
        item_id="ast_789",
        filename="logo.png",
    )
    assert key == "workspaces/ws_123/projects/prj_456/assets/ast_789/logo.png"

    # Traversal rejection
    with pytest.raises(StorageSecurityError):
        build_storage_key("ws_123", "prj_456", "assets", "ast_789", "../secret.txt")

    with pytest.raises(StorageSecurityError):
        build_storage_key("ws_123", "../prj_456", "assets", "ast_789", "logo.png")

    with pytest.raises(StorageSecurityError):
        validate_storage_key("/etc/passwd")

    with pytest.raises(StorageSecurityError):
        validate_storage_key("workspaces/ws_1/../../../root.txt")


def test_local_storage_backend(tmp_path: Path):
    storage = LocalStorageBackend(root_dir=tmp_path)
    key = "workspaces/ws_1/projects/prj_1/assets/a1/image.png"

    assert not storage.exists(key)
    with pytest.raises(StorageNotFoundError):
        storage.get(key)

    # Put bytes
    content = b"\x89PNG\r\n\x1a\nfakeimagebytes"
    meta = storage.put(key, content, content_type="image/png")
    assert meta.key == key
    assert meta.size_bytes == len(content)
    assert meta.content_type == "image/png"
    assert meta.sha256 is not None
    assert storage.exists(key)

    # Get bytes
    retrieved = storage.get(key)
    assert retrieved == content

    # Open stream
    with storage.open(key) as f:
        assert f.read() == content

    # Metadata
    info = storage.metadata(key)
    assert info.size_bytes == len(content)
    assert info.sha256 == meta.sha256

    # Signed URL
    url = storage.signed_url(key, expires_in_seconds=60)
    assert "key=" in url
    assert "signature=" in url

    # Copy
    dst_key = "workspaces/ws_1/projects/prj_1/assets/a2/image_copy.png"
    copy_meta = storage.copy(key, dst_key)
    assert copy_meta.key == dst_key
    assert storage.get(dst_key) == content

    # Delete
    assert storage.delete(key) is True
    assert not storage.exists(key)
    assert storage.delete(key) is False


def test_local_storage_traversal_rejection(tmp_path: Path):
    storage = LocalStorageBackend(root_dir=tmp_path)
    with pytest.raises(StorageSecurityError):
        storage.put("../outside.txt", b"danger")

    with pytest.raises(StorageSecurityError):
        storage.get("foo/../../etc/passwd")


def test_s3_compatible_storage_backend():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ETag": '"abc123etag"'}
    mock_client.get_object.return_value = {"Body": io.BytesIO(b"s3_data_payload")}
    mock_client.head_object.return_value = {
        "ContentLength": 15,
        "ContentType": "video/mp4",
        "ETag": '"abc123etag"',
        "LastModified": "2026-09-30T00:00:00Z",
    }
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/signed?sig=123"

    backend = S3CompatibleStorageBackend(
        bucket_name="test-bucket",
        client=mock_client,
    )

    key = "workspaces/ws_1/projects/prj_1/outputs/r1/out.mp4"

    # Put
    meta = backend.put(key, b"s3_data_payload", content_type="video/mp4")
    assert meta.key == key
    assert meta.size_bytes == 15
    assert meta.etag == "abc123etag"
    mock_client.put_object.assert_called_once()

    # Get
    data = backend.get(key)
    assert data == b"s3_data_payload"

    # Exists & Metadata
    assert backend.exists(key) is True
    m = backend.metadata(key)
    assert m.size_bytes == 15

    # Signed URL
    url = backend.signed_url(key)
    assert url == "https://s3.example.com/signed?sig=123"

    # Delete
    assert backend.delete(key) is True
    mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=key)
