-- ============================================================================
-- 003_artifact_scanning.sql  ·  owners: DEP, CNT, BIN, IAC (ONE file, one PR)
-- findings.source_context KEEPS its existing meaning (reachability:
-- SOURCE | TEST_ONLY | DEMO_ONLY). It gains NO fourth value.
-- What kind of artefact produced the finding is a separate axis.
-- ============================================================================
ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_type TEXT NOT NULL DEFAULT 'SOURCE_FILE';
    -- SOURCE_FILE | DEPENDENCY_MANIFEST | CONFIG_FILE | BINARY | CONTAINER_LAYER
ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_ref      TEXT;
    -- binary: "<section>+0x<offset>" · container: layer path · manifest: file path
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_ecosystem TEXT;
    -- pypi | npm | maven | deb | apk | rpm
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_name      TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_version   TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS image_digest      TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS layer_digest      TEXT;

CREATE INDEX IF NOT EXISTS idx_findings_artifact_type ON findings(artifact_type);
CREATE INDEX IF NOT EXISTS idx_findings_package
    ON findings(package_ecosystem, package_name)
    WHERE package_name IS NOT NULL;

-- scans.scan_context ALREADY EXISTS and carries the image reference / target
-- descriptor. No scans.target_type column is added: one scan may legitimately
-- mix source, config, manifest and binary artefacts in a single tree.
