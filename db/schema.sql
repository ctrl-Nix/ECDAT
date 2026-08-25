-- ============================================================================
-- ECDAT / PS 26164 - Enterprise Cryptographic Discovery & Quantum-Risk Platform
-- Canonical database schema (PostgreSQL)
--
-- Owner: Ronak (DATABASE lane).
-- Single source of truth for the DB. Applied automatically when the Postgres
-- container first starts (mounted into /docker-entrypoint-initdb.d by
-- docker-compose.yml). The SQLAlchemy models in db/models.py mirror it exactly.
--
-- The `findings` table stores the FULL pipeline output so nothing is dropped
-- between scan and dashboard (see CODEBASE_AUDIT.md §3.2 / §4):
--   * scanner evidence   -> scanner/finding.py
--   * risk interpretation -> api/services/risk_engine.py
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
    started_at TIMESTAMPTZ DEFAULT now(),
    status     TEXT DEFAULT 'pending'
               CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_scans_repo_id ON scans(repo_id);

-- ---------------------------------------------------------------------------
-- findings: one row per cryptographic artefact discovered in a scan.
-- Columns mirror the scanner Finding contract plus the risk-engine output.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    id                      SERIAL PRIMARY KEY,
    scan_id                 INTEGER REFERENCES scans(id) ON DELETE CASCADE,

    -- Scanner evidence (scanner/finding.py)
    file                    TEXT NOT NULL,
    line                    INTEGER NOT NULL,
    algorithm               TEXT NOT NULL,
    matched_call            TEXT,
    library                 TEXT,
    primitive               TEXT,               -- hash | cipher | signature | ...
    language                TEXT,               -- python | java | javascript
    weak_by_default         BOOLEAN,
    key_size                INTEGER,
    confidence              TEXT DEFAULT 'high',        -- high | unverified
    detection_method        TEXT DEFAULT 'static_analysis',

    -- Risk-engine interpretation (api/services/risk_engine.py)
    risk_tier               TEXT,               -- LOW | MEDIUM | HIGH | CRITICAL
    risk_reason             TEXT,
    criticality             TEXT DEFAULT 'MEDIUM',      -- MEDIUM | HIGH | CRITICAL
    quantum_vulnerable      BOOLEAN,
    classical_broken        BOOLEAN,
    recommended_replacement TEXT,
    recommendation_type     TEXT,               -- classical | hybrid | post-quantum

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT findings_risk_tier_valid
        CHECK (risk_tier IS NULL
               OR risk_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT findings_criticality_valid
        CHECK (criticality IN ('MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT findings_recommendation_type_valid
        CHECK (recommendation_type IS NULL
               OR recommendation_type IN ('classical', 'hybrid', 'post-quantum'))
);

-- Day-4 indexes (owned by Ronak): the dashboard filters findings by scan and
-- by risk tier.
CREATE INDEX IF NOT EXISTS idx_findings_scan_id  ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(risk_tier);
