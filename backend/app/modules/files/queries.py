GET_FOLDER_BY_ID = """
SELECT id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.folders
WHERE id = $1
"""

GET_FILE_BY_ID = """
SELECT id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
       path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.files
WHERE id = $1
"""
GET_STORAGE_USAGE = """
SELECT COALESCE(SUM(size_bytes), 0)::BIGINT AS used_bytes
FROM nephos.files
WHERE owner_id = $1 AND is_trashed = FALSE
"""

# Check current usage and limit
GET_USER_STORAGE_QUOTA = """
    SELECT storage_used, storage_quota
    FROM nephos.users
    WHERE id = $1
"""

CHECK_STORAGE_AVAILABLE = """
    SELECT (storage_used + $2) <= storage_quota AS has_space
    FROM nephos.users
    WHERE id = $1
"""

RECALCULATE_USER_STORAGE = """
    UPDATE nephos.users
    SET storage_used = COALESCE((
        SELECT SUM(size_bytes)
        FROM nephos.files
        WHERE owner_id = $1 AND is_trashed = FALSE
    ), 0),
    updated_at = CURRENT_TIMESTAMP
    WHERE id = $1
    RETURNING storage_used;
"""

CREATE_FOLDER = """
INSERT INTO nephos.folders (owner_id, parent_folder_id, folder_name)
VALUES ($1, $2, $3)
RETURNING id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
"""

CREATE_FILE = """
INSERT INTO nephos.files (
    id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
          path, is_trashed, trashed_at, created_at, updated_at
"""

CALL_MOVE_FOLDER = """
SELECT nephos.move_folder(
    p_folder_id => $1,
    p_dest_parent_folder_id => $2,
    p_on_collision => $3,
    p_file_mode => $4,
    p_file_decisions => $5
)
"""

CALL_MOVE_FILE = """
SELECT nephos.move_file(
    p_file_id => $1,
    p_dest_parent_folder_id => $2,
    p_on_collision => $3
)
"""

GET_FOLDER_BY_PARENT_AND_NAME = """
SELECT id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.folders
WHERE parent_folder_id IS NOT DISTINCT FROM $1
  AND folder_name = $2
  AND owner_id = $3
  AND is_trashed = FALSE
"""

GET_FILE_BY_PARENT_AND_NAME = """
SELECT id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
       path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.files
WHERE parent_folder_id IS NOT DISTINCT FROM $1
  AND file_name = $2
  AND owner_id = $3
  AND is_trashed = FALSE
"""

TRASH_FOLDER = """
UPDATE nephos.folders
SET is_trashed = TRUE,
    trashed_at = COALESCE(trashed_at, $2)
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
"""

TRASH_FILE = """
UPDATE nephos.files
SET is_trashed = TRUE,
    trashed_at = COALESCE(trashed_at, $2)
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
          path, is_trashed, trashed_at, created_at, updated_at
"""

GET_FOLDER_ACL = """
SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, permission, revoked_at,
       created_by, created_at, updated_at
FROM nephos.acl_entries
WHERE id = $1
"""

CREATE_ACL_ENTRY = """
INSERT INTO nephos.acl_entries (
    file_id, folder_id, principal_type, grantee_id, share_token,
    password_hash, permission, created_by
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (file_id, grantee_id) WHERE principal_type = 'user' AND revoked_at IS NULL
DO UPDATE SET permission = EXCLUDED.permission
RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
          revoked_at, created_by, created_at, updated_at
"""

CREATE_ACL_ENTRY_FOLDER = """
INSERT INTO nephos.acl_entries (
    file_id, folder_id, principal_type, grantee_id, share_token,
    password_hash, permission, created_by
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (folder_id, grantee_id) WHERE principal_type = 'user' AND revoked_at IS NULL
DO UPDATE SET permission = EXCLUDED.permission
RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
          revoked_at, created_by, created_at, updated_at
"""

UPDATE_ACL_ENTRY_PERMISSION = """
UPDATE nephos.acl_entries
SET permission = $2
WHERE id = $1 AND revoked_at IS NULL
RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
          revoked_at, created_by, created_at, updated_at
"""

UPDATE_LIVE_PUBLIC_LINK = """
UPDATE nephos.acl_entries
SET share_token = $2,
    password_hash = $3,
    permission = $4
WHERE id = $1 AND revoked_at IS NULL
RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
          revoked_at, created_by, created_at, updated_at
"""

REVOKE_ACL_ENTRY = """
UPDATE nephos.acl_entries
SET revoked_at = COALESCE(revoked_at, NOW())
WHERE id = $1
RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
          revoked_at, created_by, created_at, updated_at
"""

GET_LIVE_USER_SHARE = """
SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
       revoked_at, created_by, created_at, updated_at
FROM nephos.acl_entries
WHERE principal_type = 'user'
  AND revoked_at IS NULL
  AND grantee_id = $3
  AND file_id IS NOT DISTINCT FROM $1
  AND folder_id IS NOT DISTINCT FROM $2
"""

GET_LIVE_PUBLIC_LINK = """
SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
       revoked_at, created_by, created_at, updated_at
FROM nephos.acl_entries
WHERE principal_type = 'public_link'
  AND revoked_at IS NULL
  AND file_id IS NOT DISTINCT FROM $1
  AND folder_id IS NOT DISTINCT FROM $2
"""


GET_TRASHED_FILES_BEFORE = """
SELECT id, storage_key
FROM nephos.files
WHERE is_trashed = TRUE
  AND trashed_at IS NOT NULL
  AND trashed_at <= $1
"""

GET_TRASHED_FOLDERS_BEFORE = """
SELECT id
FROM nephos.folders
WHERE is_trashed = TRUE
  AND trashed_at IS NOT NULL
  AND trashed_at <= $1
"""


GET_FILES_BY_OWNER = """
SELECT id, storage_key
FROM nephos.files
WHERE owner_id = $1
"""


GET_FILES_UNDER_PATH = """
SELECT id, storage_key
FROM nephos.files
WHERE path <@ $1
"""

GET_ALL_TRASHED_FILES_BY_OWNER = """
SELECT id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
       path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.files
WHERE owner_id = $1 AND is_trashed = TRUE
  AND ($2::uuid IS NULL AND parent_folder_id IS NULL OR parent_folder_id = $2)
"""

GET_ALL_TRASHED_FOLDERS_BY_OWNER = """
SELECT id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.folders
WHERE owner_id = $1 AND is_trashed = TRUE
  AND ($2::uuid IS NULL AND parent_folder_id IS NULL OR parent_folder_id = $2)
"""
DELETE_FILE_BY_ID = """
DELETE FROM nephos.files WHERE id = $1
"""

DELETE_FOLDER_BY_ID = """
DELETE FROM nephos.folders WHERE id = $1
"""

DELETE_FILES_UNDER_PATH = """
DELETE FROM nephos.files WHERE path <@ $1
"""

DELETE_FOLDERS_UNDER_PATH = """
DELETE FROM nephos.folders WHERE path <@ $1
"""

DELETE_TRASHED_FILES_BY_OWNER = """
DELETE FROM nephos.files WHERE owner_id = $1 AND is_trashed = TRUE
"""

DELETE_TRASHED_FOLDERS_BY_OWNER = """
DELETE FROM nephos.folders WHERE owner_id = $1 AND is_trashed = TRUE
"""

GET_PATH_FOR_FILE = """
SELECT path FROM nephos.files WHERE id = $1
"""

GET_PATH_FOR_FOLDER = """
SELECT path FROM nephos.folders WHERE id = $1
"""

GET_OWNER_AND_TRASHED_FOR_FILE = """
SELECT owner_id, is_trashed FROM nephos.files WHERE id = $1
"""

GET_OWNER_AND_TRASHED_FOR_FOLDER = """
SELECT owner_id, is_trashed FROM nephos.folders WHERE id = $1
"""

GET_EFFECTIVE_PERMISSION = """
SELECT nephos.effective_permission($1, $2, $3, $4)
"""

NAME_EXISTS = """
  SELECT nephos.name_exists(
      p_is_file => $1,
      p_parent_folder_id => $2,
      p_owner_id => $3,
      p_name => $4,
      p_exclude_id => $5
  );
"""

CALL_LOCK_NAMING_SCOPE = """
SELECT nephos.lock_naming_scope($1, $2)
"""

RESOLVE_FILE_NAME_COLLISION = """
SELECT nephos.resolve_file_name_collision($1, $2, $3)
"""

RESOLVE_RESTORED_FILE_NAME = """
SELECT nephos.resolve_restored_file_name($1, $2, $3)
"""

RESOLVE_RESTORED_FOLDER_NAME = """
SELECT nephos.resolve_restored_folder_name($1, $2, $3)
"""

RESTORE_FILE = """
UPDATE nephos.files
SET is_trashed = FALSE,
    trashed_at = NULL,
    file_name = $2
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
          path, is_trashed, trashed_at, created_at, updated_at
"""

RESTORE_FOLDER = """
UPDATE nephos.folders
SET is_trashed = FALSE,
    trashed_at = NULL,
    folder_name = $2
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
"""

GET_USER_FOLDERS = """
SELECT id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.folders
WHERE owner_id = $1 AND is_trashed = FALSE
  AND ($2::uuid IS NULL AND parent_folder_id IS NULL OR parent_folder_id = $2)
"""

GET_USER_FILES = """
SELECT id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
       path, is_trashed, trashed_at, created_at, updated_at
FROM nephos.files
WHERE owner_id = $1 AND is_trashed = FALSE
  AND ($2::uuid IS NULL AND parent_folder_id IS NULL OR parent_folder_id = $2)
"""

GET_SHARED_WITH_ME_FOLDERS = """
SELECT f.id, f.owner_id, f.parent_folder_id, f.folder_name, f.path, f.is_trashed, f.trashed_at, f.created_at, f.updated_at
FROM nephos.folders f
JOIN nephos.acl_entries acl ON acl.folder_id = f.id
WHERE acl.grantee_id = $1
  AND acl.revoked_at IS NULL
  AND f.is_trashed = FALSE
"""

GET_SHARED_WITH_ME_FILES = """
SELECT f.id, f.owner_id, f.parent_folder_id, f.storage_key, f.file_name, f.size_bytes, f.mime_type, f.content_hash,
       f.path, f.is_trashed, f.trashed_at, f.created_at, f.updated_at
FROM nephos.files f
JOIN nephos.acl_entries acl ON acl.file_id = f.id
WHERE acl.grantee_id = $1
  AND acl.revoked_at IS NULL
  AND f.is_trashed = FALSE
"""

GET_FOLDERS_BY_IDS = """
SELECT id, folder_name
FROM nephos.folders
WHERE id = ANY($1::uuid[])
"""