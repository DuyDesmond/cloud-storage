from pydantic import BaseModel, EmailStr
from typing import Literal, Optional, List
from uuid import UUID
from datetime import datetime

class ShareBaseRequest(BaseModel):
    target_id: UUID
    is_file: bool

class ShareWithUserRequest(ShareBaseRequest):
    email: EmailStr
    permission: Literal['view', 'edit'] = 'view'

class UpdateUserShareRequest(ShareWithUserRequest):
    pass

class RevokeUserShareRequest(ShareBaseRequest):
    email: EmailStr

class SetPublicLinkRequest(ShareBaseRequest):
    permission: Literal['view', 'edit'] = 'view'
    password: Optional[str] = None
    enabled: bool = True

class RevokePublicLinkRequest(ShareBaseRequest):
    pass

class SharedUserResponse(BaseModel):
    email: str
    name: str
    permission: Literal['view', 'edit']

class PublicLinkStateResponse(BaseModel):
    enabled: bool
    permission: Literal['view', 'edit']
    has_password: bool
    link: Optional[str] = None

class ShareStateResponse(BaseModel):
    public_link: PublicLinkStateResponse
    users: List[SharedUserResponse]

class GenericMessageResponse(BaseModel):
    message: str
