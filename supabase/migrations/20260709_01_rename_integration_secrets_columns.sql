DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'integration_secrets' AND column_name = 'key_name'
    ) THEN
        ALTER TABLE integration_secrets RENAME COLUMN key_name TO label;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'integration_secrets' AND column_name = 'platform'
    ) THEN
        ALTER TABLE integration_secrets RENAME COLUMN platform TO provider;
    END IF;
END $$;
