-- ============================================================================
-- ECDAT / PS 26164 - Enterprise Cryptographic Discovery & Quantum-Risk Platform
-- Canonical database schema (PostgreSQL)
--
-- Owner: Ronak (DATABASE lane).
-- This schema is the one documented in ARCHITECTURE.md and is the single source
-- of truth for the DB. It is applied automatically when the Postgres container
-- first starts (mounted into /docker-entrypoint-initdb.d by docker-compose.yml).
-- The SQLAlchemy models in backend/db/models.py mirror it exactly.
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
    url  TEXT
);

-- ---------------------------------------------------------------------------
-- scans: one row per scan run against a repository.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id         SERIAL PRIMARY KEY,
    repo_id    INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT now(),
    status     TEXT DEFAULT 'pending'   -- pending | running | completed | failed
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

    -- Risk fields (see skills/cbom-quantum-risk/SKILL.md)
    risk_tier   TEXT,            -- LOW / MEDIUM / HIGH / CRITICAL
    risk_reason TEXT,            -- one-sentence, factor-based explanation

    -- PS 26164 requires classification by type, lifetime and business
    -- criticality. This column is reserved from Day 1 so no one has to touch
    -- DB/API/frontend again later to add it.
    criticality TEXT DEFAULT 'MEDIUM'   -- CRITICAL / HIGH / MEDIUM
);

-- Day-4 indexes (owned by Ronak): the dashboard filters findings by scan and
-- by risk tier.
CREATE INDEX IF NOT EXISTS idx_findings_scan_id  ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(risk_tier);
