-- ECDAT secure-reporting migration for existing PostgreSQL deployments.
-- New deployments receive the same shape from db/schema.sql.

ALTER TABLE repositories ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS external_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_repositories_org_external
    ON repositories (organization_id, external_id)
    WHERE external_id IS NOT NULL;

ALTER TABLE scans ADD COLUMN IF NOT EXISTS source_scan_id TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS scan_context TEXT;

ALTER TABLE findings ADD COLUMN IF NOT EXISTS matched_call TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS library TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS primitive TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS weak_by_default BOOLEAN;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS detection_method TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS source_context TEXT NOT NULL DEFAULT 'SOURCE';
CREATE INDEX IF NOT EXISTS idx_findings_source_context ON findings(source_context);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER NOT NULL UNIQUE REFERENCES findings(id) ON DELETE CASCADE,
    risk_model_version TEXT NOT NULL,
    classical_broken BOOLEAN NOT NULL DEFAULT FALSE,
    quantum_vulnerable BOOLEAN NOT NULL DEFAULT FALSE,
    hndl_exposure TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_replacement TEXT,
    recommendation_type TEXT,
    migration_effort_days INTEGER,
    data_shelf_life_years DOUBLE PRECISION,
    quantum_threat_horizon_years DOUBLE PRECISION,
    assumption_source TEXT,
    assessed_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    report_id TEXT NOT NULL UNIQUE,
    scan_id INTEGER NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    bundle_digest TEXT NOT NULL UNIQUE,
    signature_algorithm TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL',
    created_at TIMESTAMP DEFAULT now(),
    expires_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reports_org_created ON reports(organization_id, created_at DESC);
