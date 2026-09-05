UPSERT_USER = """
    INSERT INTO storage.users (id, email, full_name)
    VALUES ($1, $2, $3)
    ON CONFLICT (id) DO UPDATE SET email = $2, full_name = $3
"""

INSERT_DELETION_JOB = """
    INSERT INTO storage.deletion_jobs (user_id, status)
    VALUES ($1, 'pending')
    ON CONFLICT (user_id) DO NOTHING
"""

FETCH_PENDING_JOB = """
    SELECT user_id, retry_count 
    FROM storage.deletion_jobs 
    WHERE status = 'pending' AND next_retry_at <= NOW()
    ORDER BY next_retry_at ASC
    LIMIT 1
"""

MARK_JOB_PROCESSING = """
    UPDATE storage.deletion_jobs 
    SET status = 'processing' 
    WHERE user_id = $1
"""

DELETE_USER = """
    DELETE FROM storage.users WHERE id = $1
"""

DELETE_JOB = """
    DELETE FROM storage.deletion_jobs WHERE user_id = $1
"""

REQUEUE_JOB = """
    UPDATE storage.deletion_jobs 
    SET status = 'pending', 
        retry_count = retry_count + 1, 
        next_retry_at = NOW() + $2::interval
    WHERE user_id = $1
"""
