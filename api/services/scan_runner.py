"""
Scan Runner — Orchestrates the full scan pipeline for ECDAT.

Pipeline per ARCHITECTURE.md:
  1. Create Scan row (status=pending)
  2. Invoke scanner subprocess (shell=False — security requirement)
  3. Parse scanner JSON output → Finding dicts
  4. Score every finding through risk_engine (deterministic, no LLM)
  5. Bulk-persist scored findings to DB
  6. Mark scan completed / failed
  7. Return scan_id

Security note: subprocess is always called with shell=False and an explicit
list of args. The target_path is never interpolated into a string command.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

import db.crud as crud
from api.core.config import settings
from api.services.risk_engine import score_findings
from scanner.confidence import CONFIDENCE_BANDS, meets_band_threshold

log = logging.getLogger(__name__)

# Maximum bytes we will read from scanner stdout to guard against runaway output.
_MAX_STDOUT_BYTES = 10 * 1024 * 1024  # 10 MB

_MIN_BAND: str = os.environ.get("SCAN_MIN_CONFIDENCE_BAND", "PROBABLE")
if _MIN_BAND not in CONFIDENCE_BANDS:
    log.warning("Invalid SCAN_MIN_CONFIDENCE_BAND=%r; falling back to PROBABLE", _MIN_BAND)
    _MIN_BAND = "PROBABLE"


def _passes_gate(finding: dict) -> bool:
    min_band = os.environ.get("SCAN_MIN_CONFIDENCE_BAND", _MIN_BAND)
    if min_band not in CONFIDENCE_BANDS:
        min_band = "PROBABLE"
    band = finding.get("confidence_band")
    if not band:
        if finding.get("confidence") == "high":
            band = "VERIFIED"
        else:
            band = "UNVERIFIED"
    return meets_band_threshold(band, min_band)



# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_scan(
    session: Session,
    target_path: str,
    repo_name: str | None = None,
    repo_url: str | None = None,
    scan_id: int | None = None,
) -> dict[str, Any]:
    """
    Execute a full scan on *target_path* and persist results.

    Args:
        session:     Active SQLAlchemy session (caller owns commit/rollback).
        target_path: Absolute or relative path to the directory/file to scan.
        repo_name:   Human-readable repo name (defaults to path basename).
        repo_url:    Optional VCS URL for deduplication.
        scan_id:     Existing queued scan to execute.  When omitted, creates a
                     new repository/scan record for direct service usage.

    Returns:
        Dict with keys: scan_id, status, finding_count, summary, errors.

    Raises:
        ValueError: If target_path does not exist or is outside the allowed roots.
    """
    target = _validate_path(target_path)

    # 1. Use the queued scan record when the API has already created one.
    # This is the normal asynchronous API path: the ID returned by POST
    # /scans must be the same ID that later receives findings and completion.
    if scan_id is not None:
        scan = crud.get_scan(session, scan_id)
        if scan is None:
            raise ValueError(f"Queued scan {scan_id} does not exist")
    else:
        # Direct service callers still receive the original convenient
        # behavior: repository deduplication followed by a new scan record.
        name = repo_name or target.name or target.parent.name
        repo = crud.get_or_create_repository(session, name=name, url=repo_url)
        session.flush()
        scan = crud.start_scan(session, repo_id=repo.id, status="pending")
        scan_id = scan.id

    # 2. Mark the one authoritative scan record as running immediately.
    session.flush()
    scan.status = "running"
    session.flush()
    log.info("Scan %d started — target=%s", scan_id, target)

    errors: list[str] = []

    try:
        # 3. Invoke scanner subprocess.
        raw_findings = _invoke_scanner(target, scan_id, errors)

        # 4. Score only evidence-backed findings meeting minimum confidence band.
        verified_findings = [
            finding for finding in raw_findings
            if _passes_gate(finding)
        ]
        if len(verified_findings) != len(raw_findings):
            log.info(
                "Scan %d withheld %d sub-threshold finding(s) from risk scoring",
                scan_id,
                len(raw_findings) - len(verified_findings),
            )
        scored = score_findings(verified_findings) if verified_findings else []

        # 5. Bulk-persist scored findings.
        if scored:
            crud.save_findings(session, scan_id=scan_id, findings=scored)
            session.flush()

        # 6. Mark complete.
        status = "completed"
        crud.complete_scan(session, scan_id, status=status)
        session.flush()

    except Exception as exc:  # noqa: BLE001
        log.exception("Scan %d failed: %s", scan_id, exc)
        errors.append(str(exc))
        crud.complete_scan(session, scan_id, status="failed")
        session.flush()
        status = "failed"
        scored = []

    summary = crud.get_risk_summary(session, scan_id)
    log.info(
        "Scan %d %s — findings=%d summary=%s errors=%d",
        scan_id, status, len(scored), summary, len(errors),
    )

    return {
        "scan_id": scan.id,
        "status": status,
        "finding_count": len(scored),
        "summary": summary,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_path(target_path: str) -> Path:
    """
    Resolve and validate the target path.

    Security: resolves symlinks and, when the optional server-local scan API is
    enabled, requires the target to remain within SCAN_WORKSPACE_ROOT. The
    default product workflow scans locally with the CLI, not through this API.
    """
    try:
        resolved = Path(target_path).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"Target path does not exist: {target_path!r}") from exc
    if settings.SCAN_WORKSPACE_ROOT is not None:
        try:
            root = settings.SCAN_WORKSPACE_ROOT.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise ValueError("Configured scan workspace root does not exist") from exc
        if resolved != root and root not in resolved.parents:
            raise ValueError("Target path is outside the configured scan workspace root")
    return resolved


def _invoke_scanner(
    target: Path,
    scan_id: int,
    errors: list[str],
) -> list[dict[str, Any]]:
    """
    Run `python -m scanner.cli <target>` as a subprocess.

    Returns a list of raw finding dicts (keys match scanner.finding.Finding).
    On scanner error, logs and appends to *errors*; returns whatever was parsed.

    Security: shell=False, arg list never joined to a shell string.
    """
    cmd = [
        sys.executable,   # same Python interpreter as the API process
        "-m", "scanner.cli",
        str(target),
    ]

    log.debug("Scan %d invoking: %s", scan_id, cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            shell=False,           # SECURITY: never True
            timeout=300,           # 5-minute hard ceiling per scan
            check=False,           # we inspect returncode ourselves
        )
    except subprocess.TimeoutExpired:
        msg = f"Scanner timed out after 300 s for scan {scan_id}"
        log.error(msg)
        errors.append(msg)
        return []
    except OSError as exc:
        msg = f"Failed to launch scanner subprocess: {exc}"
        log.error(msg)
        errors.append(msg)
        return []

    # Log stderr for debug visibility regardless of exit code.
    if result.stderr:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        if stderr_text:
            log.debug("Scan %d scanner stderr:\n%s", scan_id, stderr_text)

    if result.returncode != 0:
        msg = (
            f"Scanner exited with code {result.returncode} for scan {scan_id}. "
            f"stderr: {(result.stderr or b'').decode('utf-8', errors='replace')[:500]}"
        )
        log.warning(msg)
        errors.append(msg)
        # Still attempt to parse partial output below.

    stdout = result.stdout
    if not stdout:
        return []

    if len(stdout) > _MAX_STDOUT_BYTES:
        msg = f"Scanner output exceeded {_MAX_STDOUT_BYTES} bytes — truncating"
        log.warning(msg)
        errors.append(msg)
        stdout = stdout[:_MAX_STDOUT_BYTES]

    return _parse_scanner_output(stdout, scan_id, errors)


def _parse_scanner_output(
    raw: bytes,
    scan_id: int,
    errors: list[str],
) -> list[dict[str, Any]]:
    """
    Parse scanner JSON output → list of finding dicts.

    The scanner CLI can emit either:
      - A JSON array  (preferred): [{"file": ..., "algorithm": ...}, ...]
      - A newline-delimited JSON stream: one JSON object per line.

    Any unparsable lines are logged and counted in errors without crashing.
    """
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return []

    # Try full JSON array first.
    if text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [f for f in data if isinstance(f, dict)]
        except json.JSONDecodeError:
            pass

    # Try newline-delimited JSON.
    findings: list[dict[str, Any]] = []
    bad_lines = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                findings.append(obj)
        except json.JSONDecodeError:
            bad_lines += 1

    if bad_lines:
        errors.append(
            f"Scan {scan_id}: {bad_lines} unparsable line(s) in scanner output"
        )

    return findings
