-- ============================================================================
-- Search cache and uploaded files
-- ============================================================================
-- Date: 2026-07-06
-- Safety: additive and idempotent.

CREATE TABLE IF NOT EXISTS search_cache (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    provider TEXT NOT NULL,
    query TEXT NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_cache_workspace_provider
    ON search_cache (workspace_id, provider);

CREATE INDEX IF NOT EXISTS idx_search_cache_expires_at
    ON search_cache (expires_at);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    analysis_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_workspace_project
    ON uploaded_files (workspace_id, project_id);

NOTIFY pgrst, 'reload schema';
