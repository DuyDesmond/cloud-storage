from app.core.config import settings
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db_connection
from app.modules.auth.dependencies import get_current_user
from app.modules.files.service import sanitize_filename

client = TestClient(app)


def test_sanitize_filename():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("hello<world>?.txt") == "helloworld.txt"
    assert sanitize_filename("  normal_file.pdf  ") == "normal_file.pdf"


def test_request_presigned_upload_unauthorized():
    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    try:
        response = client.post(
            f"{settings.API_STR}/storage/upload/presign",
            json={"file_name": "test.txt", "size_bytes": 100},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_presigned_upload_and_complete_flow():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.modules.files.service.R2StorageGateway.generate_presigned_put_url", new_callable=AsyncMock) as mock_gen, \
             patch("app.modules.files.service.R2StorageGateway.head_object", new_callable=AsyncMock) as mock_head, \
             patch("app.modules.files.repository.FileOperationsRepository.call_lock_naming_scope", new_callable=AsyncMock), \
             patch("app.modules.files.repository.FileOperationsRepository.resolve_file_name_collision", new_callable=AsyncMock, return_value="test.txt"), \
             patch("app.modules.files.repository.FileOperationsRepository.create_file", new_callable=AsyncMock) as mock_create:

            mock_gen.return_value = "https://r2.cloudflarestorage.com/nephos/test.txt?presigned=true"

            mock_head.return_value = {
                "ContentLength": 100,
                "ETag": '"sha256hash"',
                "ChecksumSHA256": "sha256hash",
                "Metadata": {
                    "content-hash": "sha256hash",
                    "sha256": "sha256hash",
                },
            }
            
            file_id = uuid.uuid4()
            storage_key = f"storage/{user_id}/1234/test.txt"
            mock_create.return_value = {
                "id": file_id,
                "owner_id": user_id,
                "parent_folder_id": None,
                "storage_key": storage_key,
                "file_name": "test.txt",
                "size_bytes": 100,
                "mime_type": "text/plain",
                "content_hash": "sha256hash",
                "path": "test",
                "is_trashed": False,
                "trashed_at": None,
                "created_at": "2026-08-10T00:00:00Z",
                "updated_at": "2026-08-10T00:00:00Z",
            }

            # 1. Request presigned URL
            res1 = client.post(
                f"{settings.API_STR}/storage/upload/presign",
                json={"file_name": "test.txt", "size_bytes": 100, "mime_type": "text/plain"},
            )
            assert res1.status_code == 200
            data1 = res1.json()
            assert "presigned_url" in data1
            assert data1["storage_key"].startswith(f"storage/{user_id}/")

            # 2. Complete upload
            res2 = client.post(
                f"{settings.API_STR}/storage/upload/complete",
                json={
                    "storage_key": data1["storage_key"],
                    "file_name": "test.txt",
                    "size_bytes": 100,
                    "mime_type": "text/plain",
                    "content_hash": "sha256hash",
                },
            )
            if res2.status_code != 201:
                print("\n[DEBUG ERROR]:", res2.status_code, res2.json())

            assert res2.status_code == 201
            data2 = res2.json()
            assert data2["id"] == str(file_id)
            assert data2["file_name"] == "test.txt"
    finally:
        app.dependency_overrides.clear()


def test_multipart_upload_flow():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.modules.files.service.R2StorageGateway.create_multipart_upload", new_callable=AsyncMock, return_value="mp-upload-id-123"), \
             patch("app.modules.files.service.R2StorageGateway.generate_presigned_part_url", new_callable=AsyncMock, return_value="https://r2.storage/part1"), \
             patch("app.modules.files.service.R2StorageGateway.complete_multipart_upload", new_callable=AsyncMock) as mock_complete_mp, \
             patch("app.modules.files.service.R2StorageGateway.abort_multipart_upload", new_callable=AsyncMock) as mock_abort_mp, \
             patch("app.modules.files.repository.FileOperationsRepository.call_lock_naming_scope", new_callable=AsyncMock), \
             patch("app.modules.files.repository.FileOperationsRepository.resolve_file_name_collision", new_callable=AsyncMock, return_value="large_file.iso"), \
             patch("app.modules.files.repository.FileOperationsRepository.create_file", new_callable=AsyncMock) as mock_create:

            file_id = uuid.uuid4()
            storage_key = f"storage/{user_id}/1234/large_file.iso"
            mock_create.return_value = {
                "id": file_id,
                "owner_id": user_id,
                "parent_folder_id": None,
                "storage_key": storage_key,
                "file_name": "large_file.iso",
                "size_bytes": 200000000,
                "mime_type": "application/octet-stream",
                "content_hash": None,
                "path": "large_file",
                "is_trashed": False,
                "trashed_at": None,
                "created_at": "2026-08-10T00:00:00Z",
                "updated_at": "2026-08-10T00:00:00Z",
            }

            # Initiate
            res1 = client.post(
                f"{settings.API_STR}/storage/upload/multipart/initiate",
                json={"file_name": "large_file.iso", "size_bytes": 200000000},
            )
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["upload_id"] == "mp-upload-id-123"

            # Presign Part
            res2 = client.post(
                f"{settings.API_STR}/storage/upload/multipart/presign-part",
                json={
                    "upload_id": data1["upload_id"],
                    "storage_key": data1["storage_key"],
                    "part_number": 1,
                },
            )
            assert res2.status_code == 200
            assert res2.json()["presigned_url"] == "https://r2.storage/part1"

            # Complete Multipart
            res3 = client.post(
                f"{settings.API_STR}/storage/upload/multipart/complete",
                json={
                    "upload_id": data1["upload_id"],
                    "storage_key": data1["storage_key"],
                    "parts": [{"part_number": 1, "etag": '"etag1"'}],
                    "file_name": "large_file.iso",
                    "size_bytes": 200000000,
                },
            )
            assert res3.status_code == 201
            mock_complete_mp.assert_called_once()

            # Abort Multipart
            res4 = client.post(
                f"{settings.API_STR}/storage/upload/multipart/abort",
                json={
                    "upload_id": data1["upload_id"],
                    "storage_key": data1["storage_key"],
                },
            )
            assert res4.status_code == 200
            mock_abort_mp.assert_called_once()
    finally:
        app.dependency_overrides.clear()