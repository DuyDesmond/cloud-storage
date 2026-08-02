GET_USER_BY_EMAIL = """
    SELECT * FROM nephos.users 
    WHERE email = $1;
"""

GET_USER_BY_ID = """
    SELECT * FROM nephos.users 
    WHERE id = $1;
"""

CREATE_USER = """
    INSERT INTO nephos.users (email, hashed_password, full_name)
    VALUES ($1, $2, $3)
    RETURNING id, email, full_name, storage_used, storage_quota, created_at;
"""

DELETE_USER = """
    DELETE FROM nephos.users 
    WHERE id = $1;
"""

CREATE_RESET_TOKEN = """
    INSERT INTO nephos.password_resets (user_id, token, expires_at)
    VALUES ($1, $2, $3);
"""

GET_VALID_RESET_TOKEN = """
    SELECT * FROM nephos.password_resets 
    WHERE token = $1 
      AND is_used = FALSE 
      AND expires_at > CURRENT_TIMESTAMP;
"""

GET_CURRENT_PASSWORD = """
    SELECT hashed_password FROM nephos.users 
    WHERE id = $1
"""

UPDATE_USER_PASSWORD = """
    UPDATE nephos.users 
    SET hashed_password = $1, 
        updated_at = CURRENT_TIMESTAMP 
    WHERE id = $2;
"""

INVALIDATE_RESET_TOKEN = """
    UPDATE nephos.password_resets 
    SET is_used = TRUE 
    WHERE id = $1;
"""