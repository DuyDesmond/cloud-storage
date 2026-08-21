from app.core.config import settings
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db_connection
from app.modules.auth.dependencies import get_current_user

client = TestClient(app)


def test_presign_upload_quota_exceeded():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.modules.files.repository.FileOperationsRepository.check_storage_available", new_callable=AsyncMock, return_value=False):
            res = client.post(
                f"{settings.API_STR}/storage/upload/presign",
                json={"file_name": "large_file.zip", "size_bytes": 100 * 1024 ** 3},
            )
            assert res.status_code == 413
            assert "Storage quota exceeded" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_complete_upload_quota_exceeded_cleans_up_blob():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        storage_key = f"storage/{user_id}/123/file.bin"
        with patch("app.modules.files.service.R2StorageGateway.head_object", new_callable=AsyncMock, return_value={"ContentLength": 5000}), \
             patch("app.modules.files.service.R2StorageGateway.delete_object", new_callable=AsyncMock) as mock_delete, \
             patch("app.modules.files.repository.FileOperationsRepository.check_storage_available", new_callable=AsyncMock, return_value=False):

            res = client.post(
                f"{settings.API_STR}/storage/upload/complete",
                json={
                    "storage_key": storage_key,
                    "file_name": "file.bin",
                    "size_bytes": 5000,
                },
            )
            assert res.status_code == 413
            assert "Storage quota exceeded" in res.json()["detail"]
            mock_delete.assert_awaited_once_with(storage_key)
    finally:
        app.dependency_overrides.clear()


def test_multipart_initiate_quota_exceeded():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.modules.files.repository.FileOperationsRepository.check_storage_available", new_callable=AsyncMock, return_value=False):
            res = client.post(
                f"{settings.API_STR}/storage/upload/multipart/initiate",
                json={"file_name": "huge.iso", "size_bytes": 50 * 1024 ** 3},
            )
            assert res.status_code == 413
            assert "Storage quota exceeded" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_restore_file_quota_exceeded():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    file_id = uuid.uuid4()
    mock_file = {
        "id": file_id,
        "owner_id": user_id,
        "parent_folder_id": None,
        "file_name": "test.txt",
        "size_bytes": 1024,
        "is_trashed": True,
    }

    try:
        with patch("app.modules.files.repository.FileOperationsRepository.get_file_by_id", new_callable=AsyncMock, return_value=mock_file), \
             patch("app.modules.files.repository.FileOperationsRepository.check_storage_available", new_callable=AsyncMock, return_value=False):

            res = client.post(f"{settings.API_STR}/storage/trash/files/{file_id}/restore")
            assert res.status_code == 413
            assert "Storage quota exceeded" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_restore_folder_quota_exceeded():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    folder_id = uuid.uuid4()
    mock_folder = {
        "id": folder_id,
        "owner_id": user_id,
        "parent_folder_id": None,
        "folder_name": "my_folder",
        "path": "my_folder",
        "is_trashed": True,
    }

    try:
        with patch("app.modules.files.repository.FileOperationsRepository.get_folder_by_id", new_callable=AsyncMock, return_value=mock_folder), \
             patch("app.modules.files.repository.FileOperationsRepository.get_folder_trashed_size", new_callable=AsyncMock, return_value=2048), \
             patch("app.modules.files.repository.FileOperationsRepository.check_storage_available", new_callable=AsyncMock, return_value=False):

            res = client.post(f"{settings.API_STR}/storage/trash/folders/{folder_id}/restore")
            assert res.status_code == 413
            assert "Storage quota exceeded" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_storage_usage_endpoint():
    user_id = uuid.uuid4()
    mock_user = {"id": user_id, "email": "test@example.com"}

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_connection] = mock_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.modules.files.repository.FileOperationsRepository.get_storage_usage", new_callable=AsyncMock, return_value=102400), \
             patch("app.modules.files.repository.FileOperationsRepository.get_user_storage_quota", new_callable=AsyncMock, return_value={"storage_quota": 21474836480}):

            res = client.get(f"{settings.API_STR}/storage/usage")
            assert res.status_code == 200
            data = res.json()
            assert data["used_bytes"] == 102400
            assert data["total_bytes"] == 21474836480
    finally:
        app.dependency_overrides.clear()