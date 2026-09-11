import secrets
import asyncpg
from typing import Optional
from fastapi import HTTPException, status
from app.modules.share.repository import ShareRepository
from app.modules.auth.repository import AuthRepository
from app.modules.share import schemas
from app.core.security import hash_password
import uuid

share_repository = ShareRepository()
auth_repository = AuthRepository()

class ShareService:
    async def _verify_owner(self, conn: asyncpg.Connection, target_id: uuid.UUID, is_file: bool, user_id: uuid.UUID) -> None:
        is_owner = await share_repository.check_is_owner(conn, target_id, is_file, user_id)
        if not is_owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action.")

    async def share_with_user(self, conn: asyncpg.Connection, request: schemas.ShareWithUserRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(conn, request.target_id, request.is_file, owner_id)
        
        # Look up user by email
        grantee = await auth_repository.get_by_email(conn, request.email)
        if not grantee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with this email not found.")
            
        grantee_id = grantee['id']
        if grantee_id == owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share file with yourself.")
            
        pwd_hash = hash_password(request.password) if request.password else None
        await share_repository.upsert_user_share(conn, request.target_id, request.is_file, grantee_id, request.permission, owner_id, pwd_hash)
        return schemas.GenericMessageResponse(message="Share updated successfully")

    async def revoke_user_share(self, conn: asyncpg.Connection, request: schemas.RevokeUserShareRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(conn, request.target_id, request.is_file, owner_id)
        
        grantee = await auth_repository.get_by_email(conn, request.email)
        if not grantee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
        await share_repository.revoke_user_share(conn, request.target_id, request.is_file, grantee['id'])
        return schemas.GenericMessageResponse(message="Share revoked successfully")

    async def set_public_link(self, conn: asyncpg.Connection, request: schemas.SetPublicLinkRequest, owner_id: uuid.UUID) -> schemas.GenericMessageResponse:
        await self._verify_owner(conn, request.target_id, request.is_file, owner_id)
        
        if not request.enabled:
            await share_repository.revoke_public_link(conn, request.target_id, request.is_file)
            return schemas.GenericMessageResponse(message="Public link disabled successfully")
            
        token = secrets.token_urlsafe(32)
        pwd_hash = hash_password(request.password) if request.password else None
        
        await share_repository.upsert_public_link(conn, request.target_id, request.is_file, token, pwd_hash, request.permission, owner_id)
        return schemas.GenericMessageResponse(message="Public link enabled successfully")

    async def get_share_state(self, conn: asyncpg.Connection, target_id: uuid.UUID, is_file: bool, owner_id: uuid.UUID) -> schemas.ShareStateResponse:
        await self._verify_owner(conn, target_id, is_file, owner_id)
        
        records = await share_repository.get_share_state(conn, target_id, is_file)
        
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

    async def visit_public_link(self, conn: asyncpg.Connection, share_token: str, user_id: uuid.UUID) -> dict:
        acl = await share_repository.get_acl_by_token(conn, share_token)
        if not acl:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found or revoked.")
        
        await share_repository.upsert_public_link_visitor(conn, user_id, acl['id'])
        
        return {
            "message": "Link visited successfully",
            "is_file": acl['file_id'] is not None,
            "target_id": acl['file_id'] or acl['folder_id']
        }
