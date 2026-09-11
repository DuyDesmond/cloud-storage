UPSERT_USER_SHARE_FILE = """
    INSERT INTO nephos.acl_entries (file_id, principal_type, grantee_id, permission, created_by, password_hash)
    VALUES ($1, 'user', $2, $3::nephos.permission_level, $4, $5)
    ON CONFLICT (file_id, grantee_id) WHERE principal_type = 'user' AND revoked_at IS NULL
    DO UPDATE SET 
        permission = EXCLUDED.permission, 
        password_hash = EXCLUDED.password_hash,
        updated_at = NOW()
    RETURNING *;
"""

UPSERT_USER_SHARE_FOLDER = """
    INSERT INTO nephos.acl_entries (folder_id, principal_type, grantee_id, permission, created_by, password_hash)
    VALUES ($1, 'user', $2, $3::nephos.permission_level, $4, $5)
    ON CONFLICT (folder_id, grantee_id) WHERE principal_type = 'user' AND revoked_at IS NULL
    DO UPDATE SET 
        permission = EXCLUDED.permission, 
        password_hash = EXCLUDED.password_hash,
        updated_at = NOW()
    RETURNING *;
"""

REVOKE_USER_SHARE_FILE = """
    UPDATE nephos.acl_entries
    SET revoked_at = NOW(), updated_at = NOW()
    WHERE file_id = $1 AND grantee_id = $2 AND principal_type = 'user' AND revoked_at IS NULL
"""

REVOKE_USER_SHARE_FOLDER = """
    UPDATE nephos.acl_entries
    SET revoked_at = NOW(), updated_at = NOW()
    WHERE folder_id = $1 AND grantee_id = $2 AND principal_type = 'user' AND revoked_at IS NULL
"""

UPSERT_PUBLIC_LINK_FILE = """
    INSERT INTO nephos.acl_entries (file_id, principal_type, share_token, password_hash, permission, created_by)
    VALUES ($1, 'public_link', $2, $3, $4::nephos.permission_level, $5)
    ON CONFLICT (file_id) WHERE principal_type = 'public_link' AND revoked_at IS NULL AND file_id IS NOT NULL
    DO UPDATE SET 
        password_hash = EXCLUDED.password_hash, 
        permission = EXCLUDED.permission, 
        updated_at = NOW()
    RETURNING share_token;
"""

UPSERT_PUBLIC_LINK_FOLDER = """
    INSERT INTO nephos.acl_entries (folder_id, principal_type, share_token, password_hash, permission, created_by)
    VALUES ($1, 'public_link', $2, $3, $4::nephos.permission_level, $5)
    ON CONFLICT (folder_id) WHERE principal_type = 'public_link' AND revoked_at IS NULL AND folder_id IS NOT NULL
    DO UPDATE SET 
        password_hash = EXCLUDED.password_hash, 
        permission = EXCLUDED.permission, 
        updated_at = NOW()
    RETURNING share_token;
"""

REVOKE_PUBLIC_LINK_FILE = """
    WITH revoked AS (
        UPDATE nephos.acl_entries
        SET revoked_at = NOW(), updated_at = NOW()
        WHERE file_id = $1 AND principal_type = 'public_link' AND revoked_at IS NULL
        RETURNING id
    )
    DELETE FROM nephos.public_link_visitors
    WHERE acl_entry_id IN (SELECT id FROM revoked)
"""

REVOKE_PUBLIC_LINK_FOLDER = """
    WITH revoked AS (
        UPDATE nephos.acl_entries
        SET revoked_at = NOW(), updated_at = NOW()
        WHERE folder_id = $1 AND principal_type = 'public_link' AND revoked_at IS NULL
        RETURNING id
    )
    DELETE FROM nephos.public_link_visitors
    WHERE acl_entry_id IN (SELECT id FROM revoked)
"""

GET_SHARE_STATE_FILE = """
    SELECT a.principal_type, a.grantee_id, a.share_token, a.password_hash, a.permission, a.revoked_at,
           u.email, u.full_name
    FROM nephos.acl_entries a
    LEFT JOIN nephos.users u ON a.grantee_id = u.id
    WHERE a.file_id = $1 AND a.revoked_at IS NULL
"""

GET_SHARE_STATE_FOLDER = """
    SELECT a.principal_type, a.grantee_id, a.share_token, a.password_hash, a.permission, a.revoked_at,
           u.email, u.full_name
    FROM nephos.acl_entries a
    LEFT JOIN nephos.users u ON a.grantee_id = u.id
    WHERE a.folder_id = $1 AND a.revoked_at IS NULL
"""

CHECK_OWNER_FILE = """
    SELECT 1 FROM nephos.files WHERE id = $1 AND owner_id = $2 AND is_trashed = FALSE
"""

CHECK_OWNER_FOLDER = """
    SELECT 1 FROM nephos.folders WHERE id = $1 AND owner_id = $2 AND is_trashed = FALSE
"""

GET_ACL_BY_TOKEN = """
    SELECT id, file_id, folder_id, principal_type, permission, password_hash
    FROM nephos.acl_entries
    WHERE share_token = $1 AND revoked_at IS NULL
"""

UPSERT_PUBLIC_LINK_VISITOR = """
    INSERT INTO nephos.public_link_visitors (user_id, acl_entry_id, last_accessed_at)
    VALUES ($1, $2, NOW())
    ON CONFLICT (user_id, acl_entry_id) 
    DO UPDATE SET last_accessed_at = NOW()
"""
