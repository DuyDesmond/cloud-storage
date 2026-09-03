-- storage_users_table.sql
CREATE TABLE IF NOT EXISTS storage.users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT
);

-- deletion_jobs_table.sql
CREATE TABLE IF NOT EXISTS storage.deletion_jobs (
    user_id UUID PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO storage.users (id, email, full_name)
SELECT id, email, full_name
FROM auth.users
ON CONFLICT (id) DO NOTHING;
