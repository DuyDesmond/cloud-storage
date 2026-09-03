import secrets
import asyncpg
from typing import Optional
from fastapi import HTTPException, status, Depends
from app.modules.share.repository import ShareRepository
from app.modules.share import schemas
from app.core.security import hash_password
from app.core.config import settings
import uuid

from app.core.cache import CacheRepository
from app.core.auth_client import AuthServiceClient

class ShareService:
    def __init__(
        self, 
        repo: ShareRepository = Depends(),
        auth_client: AuthServiceClient = Depends(),
        cache: CacheRepository = Depends()
    ):
        self.repo = repo
        self.auth_client = auth_client
        self.cache = cache
    async def _verify_owner(self, target_id: uuid.UUID, is_file: bool, user_id: uuid.UUID) -> None:
        is_owner = await self.repo.check_is_owner(target_id, is_file, user_id)
        if not is_owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action.")

    async def share_with_user(self, request: schemas.ShareWithUserRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(request.target_id, request.is_file, owner_id)
        
        # Look up user by email via local read-replica table
        grantee = await self.repo.get_user_by_email(request.email)
        if not grantee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with this email not found.")
            
        grantee_id = grantee['id']
        if grantee_id == owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share file with yourself.")
            
        pwd_hash = hash_password(request.password) if request.password else None
        await self.repo.upsert_user_share(request.target_id, request.is_file, grantee_id, request.permission, owner_id, pwd_hash)
        return schemas.GenericMessageResponse(message="Share updated successfully")

    async def revoke_user_share(self, request: schemas.RevokeUserShareRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(request.target_id, request.is_file, owner_id)
        
        grantee = await self.repo.get_user_by_email(request.email)
        if not grantee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
        await self.repo.revoke_user_share(request.target_id, request.is_file, grantee['id'])
        return schemas.GenericMessageResponse(message="Share revoked successfully")

    async def set_public_link(self, request: schemas.SetPublicLinkRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(request.target_id, request.is_file, owner_id)
        
        if not request.enabled:
            await self.repo.revoke_public_link(request.target_id, request.is_file)
            return schemas.GenericMessageResponse(message="Public link disabled successfully")
            
        token = secrets.token_urlsafe(32)
        pwd_hash = hash_password(request.password) if request.password else None
        
        await self.repo.upsert_public_link(request.target_id, request.is_file, token, pwd_hash, request.permission, owner_id)
        return schemas.GenericMessageResponse(message="Public link enabled successfully")

    async def get_share_state(self, target_id: uuid.UUID, is_file: bool, owner_id: uuid.UUID) -> schemas.ShareStateResponse:
        await self._verify_owner(target_id, is_file, owner_id)
        
        records = await self.repo.get_share_state(target_id, is_file)
        
        users = []
        public_link = schemas.PublicLinkStateResponse(enabled=False, permission="view", has_password=False, link=None)
        
        for r in records:
            if r['principal_type'] == 'user':
                users.append(schemas.SharedUserResponse(
                    email=r['email'],
                    name=r['full_name'],
                    permission=r['permission'],
                    has_password=r['password_hash'] is not None
                ))
            elif r['principal_type'] == 'public_link':
                public_link.enabled = True
                public_link.permission = r['permission']
                public_link.has_password = r['password_hash'] is not None
                public_link.link = r['share_token'] # The UI can construct the full URL
                
        return schemas.ShareStateResponse(public_link=public_link, users=users)

    async def visit_public_link(self, share_token: str, user_id: uuid.UUID | None) -> dict:
        acl = await self.cache.get_share_acl(share_token)
        if acl:
            # Reconstruct UUID fields natively
            if "id" in acl and acl["id"]:
                acl["id"] = uuid.UUID(acl["id"])
            if "file_id" in acl and acl["file_id"]:
                acl["file_id"] = uuid.UUID(acl["file_id"])
            if "folder_id" in acl and acl["folder_id"]:
                acl["folder_id"] = uuid.UUID(acl["folder_id"])
                    
        if not acl:
            acl_row = await self.repo.get_acl_by_token(share_token)
            if not acl_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found or revoked.")
            acl = dict(acl_row)
            
            # Cache for 10 minutes to protect against viral traffic bursts
            await self.cache.set_share_acl(share_token, acl, ttl_seconds=600)
        
        if user_id and not (acl.get('created_by') and str(user_id) == str(acl['created_by'])):
            await self.repo.upsert_public_link_visitor(user_id, acl['id'])
        
        return {
            "message": "Link visited successfully",
            "is_file": acl['file_id'] is not None,
            "target_id": acl['file_id'] or acl['folder_id'],
            "file_name": acl.get('file_name'),
            "mime_type": acl.get('mime_type'),
            "size_bytes": acl.get('size_bytes')
        }
