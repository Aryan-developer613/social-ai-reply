-- ============================================================================
-- Content calendar planning and approval
-- ============================================================================
-- Adds lightweight scheduling metadata to post_drafts so AI-generated social
-- content can move from suggested draft -> approved scheduled item without
-- requiring immediate platform publishing integrations.
-- ============================================================================

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'reddit';

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS body TEXT;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS source_prompt TEXT;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS thread_json JSONB DEFAULT '[]'::jsonb;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft';

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS source_reply_draft_id INT NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS source_opportunity_id INT NULL;

UPDATE post_drafts
SET body = content
WHERE body IS NULL
  AND content IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_post_drafts_project_schedule
    ON post_drafts(project_id, scheduled_at);

CREATE INDEX IF NOT EXISTS idx_post_drafts_project_platform_status
    ON post_drafts(project_id, platform, status);
