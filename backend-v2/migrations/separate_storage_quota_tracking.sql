BEGIN;

-- 1. Ensure storage schema exists
CREATE SCHEMA IF NOT EXISTS storage;

-- 2. Create the new storage.user_quotas table
CREATE TABLE IF NOT EXISTS storage.user_quotas (
    user_id UUID PRIMARY KEY,
    storage_used BIGINT NOT NULL DEFAULT 0,
    storage_quota BIGINT NOT NULL DEFAULT 21474836480,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Copy existing data from auth.users
INSERT INTO storage.user_quotas (user_id, storage_used, storage_quota)
SELECT id, COALESCE(storage_used, 0), COALESCE(storage_quota, 21474836480)
FROM auth.users
ON CONFLICT (user_id) DO UPDATE SET
    storage_used = EXCLUDED.storage_used,
    storage_quota = EXCLUDED.storage_quota;

-- 4. Safely drop columns from auth.users
ALTER TABLE auth.users DROP COLUMN IF EXISTS storage_used;
ALTER TABLE auth.users DROP COLUMN IF EXISTS storage_quota;

COMMIT;
