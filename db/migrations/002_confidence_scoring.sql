-- ============================================================================
-- 002_confidence_scoring.sql  ·  owner: CONF
-- Unified, auditable confidence. Legacy findings.confidence TEXT is RETAINED
-- and becomes a derived, read-only mirror of confidence_band so existing rows,
-- CBOM output and the CLI contract do not break on day one.
-- ============================================================================
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_score   NUMERIC(3,2);
    -- 0.00–1.00. NUMERIC over SMALLINT: displayed as a percentage, no unit ambiguity.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_band    TEXT;
    -- VERIFIED | PROBABLE | UNVERIFIED. NULL == pre-model legacy row.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_signals JSONB;
    -- named evidence signals, e.g. ["import_resolved","literal_algorithm_arg"]
CREATE INDEX IF NOT EXISTS idx_findings_confidence_band ON findings(confidence_band);
