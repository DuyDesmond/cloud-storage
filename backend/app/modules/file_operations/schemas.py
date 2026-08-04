from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, Field


PermissionLevel = Literal["view", "edit"]
PrincipalType = Literal["user", "public_link"]
TargetType = Literal["file", "folder"]


class FolderCreateRequest(BaseModel):
    folder_name: str = Field(min_length=1, max_length=255)
    parent_folder_id: uuid.UUID | None = None


class FolderMoveRequest(BaseModel):
    parent_folder_id: uuid.UUID | None = None


class FileMoveRequest(BaseModel):
    parent_folder_id: uuid.UUID | None = None


class ShareCreateRequest(BaseModel):
    target_type: TargetType
    target_id: uuid.UUID
    principal_type: PrincipalType
    grantee_id: uuid.UUID | None = None
    share_token: str | None = None
    password: str | None = None
    expires_at: datetime | None = None
    permission: PermissionLevel = "view"


class ShareResponse(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID | None
    folder_id: uuid.UUID | None
    principal_type: PrincipalType
    grantee_id: uuid.UUID | None
    share_token: str | None
    permission: PermissionLevel
    revoked_at: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class FolderResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    parent_folder_id: uuid.UUID | None
    folder_name: str
    path: str
    is_trashed: bool
    trashed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FileResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    parent_folder_id: uuid.UUID | None
    storage_key: str
    file_name: str
    size_bytes: int
    mime_type: str | None
    content_hash: str | None
    path: str
    is_trashed: bool
    trashed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str
