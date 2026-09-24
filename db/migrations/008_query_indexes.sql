CREATE INDEX IF NOT EXISTS idx_findings_scan_tier   ON findings(scan_id, risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_scan_lang   ON findings(scan_id, language);
CREATE INDEX IF NOT EXISTS idx_scans_repo_started   ON scans(repo_id, started_at DESC);
