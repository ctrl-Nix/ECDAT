-- ============================================================================
-- ECDAT / PS 26164 - Enterprise Cryptographic Discovery & Quantum-Risk Platform
-- Canonical database schema (PostgreSQL)
--
-- Owner: Ronak (DATABASE lane).
-- This schema is the one documented in ARCHITECTURE.md and is the single source
-- of truth for the DB. It is applied automatically when the Postgres container
-- first starts (mounted into /docker-entrypoint-initdb.d by docker-compose.yml).
-- The SQLAlchemy models in db/models.py mirror it exactly.
--
-- Classification model (per PS 26164 wording): findings are classified by type,
-- lifetime and business criticality, and risk-scored via Mosca's algorithm.
--   risk_tier / risk_reason -> quantum-risk score (see skills/cbom-quantum-risk)
--   criticality             -> business criticality (CRITICAL/HIGH/MEDIUM)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- repositories: one row per codebase / target the tool has scanned.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url  TEXT,
    organization_id TEXT,
    external_id TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_repositories_org_external
    ON repositories (organization_id, external_id)
    WHERE external_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL,
    organization_id TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now(),
    last_login_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);

-- ---------------------------------------------------------------------------
-- scans: one row per scan run against a repository.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id         SERIAL PRIMARY KEY,
    repo_id    INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT now(),
    status     TEXT DEFAULT 'pending',  -- pending | running | completed | failed
    source_scan_id TEXT,
    scan_context TEXT
);

-- ---------------------------------------------------------------------------
-- findings: one row per cryptographic artefact discovered in a scan.
-- Column names follow the scanner finding contract: file, line, algorithm,
-- key_size, confidence. Risk columns are populated by the CBOM/quantum-risk
-- step.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    id          SERIAL PRIMARY KEY,
    scan_id     INTEGER REFERENCES scans(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,
    line        INTEGER NOT NULL,
    algorithm   TEXT NOT NULL,
    key_size    INTEGER,
    confidence  TEXT DEFAULT 'high',
    matched_call TEXT,
    library TEXT,
    primitive TEXT,
    language TEXT,
    weak_by_default BOOLEAN,
    detection_method TEXT,
    source_context TEXT NOT NULL DEFAULT 'SOURCE',

    -- Risk fields (see skills/cbom-quantum-risk/SKILL.md)
    risk_tier   TEXT,            -- LOW / MEDIUM / HIGH / CRITICAL
    risk_reason TEXT,            -- one-sentence, factor-based explanation

    -- PS 26164 requires classification by type, lifetime and business
    -- criticality. This column is reserved from Day 1 so no one has to touch
    -- DB/API/frontend again later to add it.
    criticality TEXT DEFAULT 'MEDIUM',   -- CRITICAL / HIGH / MEDIUM

    -- Unified confidence scoring (CONF)
    confidence_score   NUMERIC(3,2),
    confidence_band    TEXT,
    confidence_signals JSONB,

    -- Artifact scanning (DEP, CNT, BIN, IAC)
    artifact_type TEXT NOT NULL DEFAULT 'SOURCE_FILE',
    artifact_ref TEXT,
    package_ecosystem TEXT,
    package_name TEXT,
    package_version TEXT,
    image_digest TEXT,
    layer_digest TEXT
);

-- Day-4 indexes (owned by Ronak): the dashboard filters findings by scan and
-- by risk tier.
CREATE INDEX IF NOT EXISTS idx_findings_scan_id  ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_source_context ON findings(source_context);
CREATE INDEX IF NOT EXISTS idx_findings_confidence_band ON findings(confidence_band);
CREATE INDEX IF NOT EXISTS idx_findings_artifact_type ON findings(artifact_type);
CREATE INDEX IF NOT EXISTS idx_findings_package
    ON findings(package_ecosystem, package_name)
    WHERE package_name IS NOT NULL;

-- Immutable interpretation and custody records. The raw finding remains a
-- discovery fact; the assessment can be recomputed under a new model version.
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
