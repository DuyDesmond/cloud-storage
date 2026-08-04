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

MOVE_FOLDER = """
UPDATE nephos.folders
SET parent_folder_id = $2
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, folder_name, path, is_trashed, trashed_at, created_at, updated_at
"""

MOVE_FILE = """
UPDATE nephos.files
SET parent_folder_id = $2
WHERE id = $1
RETURNING id, owner_id, parent_folder_id, storage_key, file_name, size_bytes, mime_type, content_hash,
          path, is_trashed, trashed_at, created_at, updated_at
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
