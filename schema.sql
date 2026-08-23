-- ============================================================================
-- PS 26164 - Enterprise Cryptographic Discovery & Quantum-Risk Analysis Platform
-- Canonical database schema (PostgreSQL 14+)
--
-- Owner: Ronak (DATABASE lane)
-- This file is the single source of truth for the relational schema. It is
-- applied automatically when the Postgres container first starts (mounted into
-- /docker-entrypoint-initdb.d by db/docker-compose.yml). It is also kept in
-- sync with the SQLAlchemy models in cbom_db/models.py -- regenerate/verify
-- with `python scripts/export_schema.py --check`.
--
-- Data flow this schema serves (from the team integration map):
--   Scanner (Shashank)            -> finding rows          -> findings
--   CBOM + risk (Maitreyi/Shashank) -> asset_type/key_size/quantum_risk columns
--   Remediation (Shreyanshi)      -> remediation / recommended_replacement
--   Backend trio (FastAPI)        -> reads/writes via cbom_db.crud
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- repositories: one row per codebase / target the tool has ever scanned.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT        NOT NULL,
    url            TEXT,
    default_branch TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- A repo is identified by its URL when present; the partial unique index
    -- below prevents duplicate rows for the same remote.
    CONSTRAINT repositories_name_not_blank CHECK (length(trim(name)) > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_repositories_url
    ON repositories (url) WHERE url IS NOT NULL;

-- ---------------------------------------------------------------------------
-- scans: one row per scan run against a repository. Holds run status and a
-- denormalized finding count so the dashboard's scan list is cheap to render.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repo_id        BIGINT      NOT NULL
                   REFERENCES repositories (id) ON DELETE CASCADE,
    commit_sha     TEXT,
    status         TEXT        NOT NULL DEFAULT 'queued',
    tool_version   TEXT,
    total_findings INTEGER     NOT NULL DEFAULT 0,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT scans_status_valid
        CHECK (status IN ('queued', 'running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_scans_repo_id     ON scans (repo_id);
-- Dashboard: "most recent scans" ordering.
CREATE INDEX IF NOT EXISTS ix_scans_started_at  ON scans (started_at DESC);

-- ---------------------------------------------------------------------------
-- findings: one row per cryptographic artefact discovered in a scan.
-- Column names map to the two agreed contracts:
--   * scanner finding contract: algorithm, file(->file_path), line, severity
--   * CBOM/CycloneDX fields:     algorithm, keyLength(->key_size),
--                                assetType(->asset_type), filePath(->file_path)
-- The full original finding is also stored verbatim in `raw` for lossless
-- CBOM export.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scan_id                 BIGINT  NOT NULL
                            REFERENCES scans (id) ON DELETE CASCADE,
    file_path               TEXT    NOT NULL,
    line                    INTEGER,
    algorithm               TEXT    NOT NULL,     -- e.g. MD5, RSA, DES, RC4
    primitive               TEXT,                 -- hash | cipher | signature | key-exchange | ...
    key_size                INTEGER,              -- CycloneDX keyLength (bits), nullable
    asset_type              TEXT    NOT NULL DEFAULT 'algorithm',  -- CycloneDX assetType
    severity                TEXT    NOT NULL,     -- info|low|medium|high|critical
    quantum_risk            TEXT,                 -- Mosca tier: low|medium|high|critical
    deprecated              BOOLEAN NOT NULL DEFAULT FALSE,
    evidence                TEXT,                 -- offending code snippet / line text
    remediation             TEXT,                 -- Shreyanshi's plain-English fix
    recommended_replacement TEXT,                 -- e.g. SHA-256, Ed25519, ML-KEM
    raw                     JSONB,                -- verbatim finding for CBOM fidelity
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT findings_severity_valid
        CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
    CONSTRAINT findings_quantum_risk_valid
        CHECK (quantum_risk IS NULL
               OR quantum_risk IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT findings_asset_type_valid
        CHECK (asset_type IN ('algorithm', 'certificate', 'protocol',
                              'related-crypto-material'))
);

-- Day-4 indexes: the dashboard's findings table filters by scan and severity.
CREATE INDEX IF NOT EXISTS ix_findings_scan_id       ON findings (scan_id);
CREATE INDEX IF NOT EXISTS ix_findings_severity      ON findings (severity);
-- Composite index covers the common "findings for this scan, filtered/sorted
-- by severity" dashboard query in a single index scan.
CREATE INDEX IF NOT EXISTS ix_findings_scan_severity ON findings (scan_id, severity);

COMMIT;
