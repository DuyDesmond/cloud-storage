BEGIN;

-- 1. Create new schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS storage;

-- Note: The FastAPI application should be run ONCE against the database to create the empty tables 
-- with the new schemas before running this data migration script.

-- 2. Migrate Auth Data
INSERT INTO auth.users (id, email, full_name, hashed_password, is_active, is_superuser, storage_used, storage_quota, created_at, updated_at)
SELECT id, email, full_name, hashed_password, is_active, is_superuser, storage_used, storage_quota, created_at, updated_at
FROM nephos.users
ON CONFLICT DO NOTHING;

INSERT INTO auth.password_resets (id, user_id, token, expires_at, is_used, created_at)
SELECT id, user_id, token, expires_at, is_used, created_at
FROM nephos.password_resets
ON CONFLICT DO NOTHING;

-- 3. Migrate Storage Data
INSERT INTO storage.folders (id, owner_id, parent_folder_id, path, folder_name, is_trashed, trashed_at, created_at, updated_at)
SELECT id, owner_id, parent_folder_id, path, folder_name, is_trashed, trashed_at, created_at, updated_at
FROM nephos.folders
ON CONFLICT DO NOTHING;

INSERT INTO storage.files (id, owner_id, parent_folder_id, path, storage_key, file_name, size_bytes, mime_type, content_hash, is_trashed, trashed_at, created_at, updated_at)
SELECT id, owner_id, parent_folder_id, path, storage_key, file_name, size_bytes, mime_type, content_hash, is_trashed, trashed_at, created_at, updated_at
FROM nephos.files
ON CONFLICT DO NOTHING;

-- Note: In v2, expires_at is removed from acl_entries, replaced by revoked_at logic.
INSERT INTO storage.acl_entries (id, file_id, folder_id, principal_type, grantee_id, share_token, password_hash, permission, created_by, created_at, updated_at)
SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, password_hash, permission, created_by, created_at, updated_at
FROM nephos.acl_entries
ON CONFLICT DO NOTHING;

INSERT INTO storage.public_link_visitors (id, user_id, acl_entry_id, last_accessed_at)
SELECT id, user_id, acl_entry_id, last_accessed_at
FROM nephos.public_link_visitors
ON CONFLICT DO NOTHING;

COMMIT;
