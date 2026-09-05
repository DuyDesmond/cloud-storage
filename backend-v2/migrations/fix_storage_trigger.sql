-- Fix trigger for storage.user_quotas

-- 1. Replace the function so it updates storage.user_quotas instead of auth.users
CREATE OR REPLACE FUNCTION storage.sync_storage_usage() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NOT NEW.is_trashed THEN
            UPDATE storage.user_quotas SET storage_used = storage_used + NEW.size_bytes WHERE user_id = NEW.owner_id;
        END IF;

    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_trashed = FALSE AND NEW.is_trashed = TRUE THEN
            UPDATE storage.user_quotas SET storage_used = storage_used - OLD.size_bytes WHERE user_id = OLD.owner_id;
        ELSIF OLD.is_trashed = TRUE AND NEW.is_trashed = FALSE THEN
            UPDATE storage.user_quotas SET storage_used = storage_used + NEW.size_bytes WHERE user_id = NEW.owner_id;
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        IF NOT OLD.is_trashed THEN
            UPDATE storage.user_quotas SET storage_used = storage_used - OLD.size_bytes WHERE user_id = OLD.owner_id;
        END IF;
    END IF;

    RETURN NULL; -- AFTER trigger, return value ignored
END;
$$ LANGUAGE plpgsql;

-- 2. Drop the old constraint from auth.users (if it still exists)
ALTER TABLE auth.users DROP CONSTRAINT IF EXISTS check_storage_within_quota;

-- 3. Add the constraint to the new table
ALTER TABLE storage.user_quotas DROP CONSTRAINT IF EXISTS check_storage_within_quota;
ALTER TABLE storage.user_quotas
    ADD CONSTRAINT check_storage_within_quota
    CHECK (storage_used <= storage_quota) NOT VALID;
ALTER TABLE storage.user_quotas VALIDATE CONSTRAINT check_storage_within_quota;
