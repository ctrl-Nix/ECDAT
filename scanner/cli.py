"""ECDAT offline source scanner and controlled report-sync CLI.

The default command performs no network operation. It scans a local target,
scores findings locally, and writes JSON to stdout. Report delivery is an explicit
signed operation requiring a user-supplied HTTPS endpoint and mTLS credentials.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from api.services.report_bundle import build_bundle, load_private_key, sign_bundle
from api.services.risk_engine import score_findings
from scanner import multilang_engine, python_engine


RULES_DIR = Path(__file__).resolve().parent / "rules"
_TIER_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNSCORED": 4}
_TEST_CONTEXT_PARTS = {"test", "tests", "__tests__", "fixtures", "fixture", "spec"}
_DEMO_CONTEXT_PARTS = {"demo", "demos", "example", "examples", "sample", "samples"}


def scan(target: Path) -> list:
    """Scan a local file or tree using all registered source-language engines."""
    rules = multilang_engine.load_rules(RULES_DIR)
    findings = []
    if target.is_dir():
        findings.extend(python_engine.scan_directory(target))
        findings.extend(multilang_engine.scan_directory(target, rules))
    elif target.suffix == ".py":
        findings.extend(python_engine.scan_file(target))
    elif target.suffix in multilang_engine.EXT_TO_LANG:
        findings.extend(multilang_engine.scan_file(target, rules))
    else:
        print(
            f"[warn] no engine registered for {target.suffix or '(no extension)'}",
            file=sys.stderr,
        )
    return findings


def _relative_or_redacted(raw_path: str, root: Path, redact_paths: bool) -> str:
    """Prevent absolute workstation paths from leaving a local scan by default."""
    try:
        relative = Path(raw_path).resolve().relative_to(root)
        return str(relative)
    except (ValueError, OSError):
        return "[redacted]" if redact_paths else raw_path


def _source_context(relative_path: str) -> str:
    """Classify path context without claiming runtime reachability."""
    parts = {part.lower() for part in Path(relative_path).parts}
    if parts & _TEST_CONTEXT_PARTS:
        return "TEST_ONLY"
    if parts & _DEMO_CONTEXT_PARTS:
        return "DEMO_ONLY"
    return "SOURCE"


def _prepare_findings(
    target: Path, redact_paths: bool, shelf_life: float | None, source_context: str | None
) -> list[dict[str, Any]]:
    root = target if target.is_dir() else target.parent
    raw = [asdict(finding) for finding in scan(target)]
    for finding in raw:
        finding["file"] = _relative_or_redacted(finding["file"], root, redact_paths)
        finding["source_context"] = source_context or _source_context(finding["file"])
        if shelf_life is not None:
            finding["data_shelf_life_years"] = shelf_life
            finding["assumption_source"] = "cli --data-shelf-life-years"
    return score_findings(raw)


def _summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    result = {tier: 0 for tier in _TIER_ORDER}
    result["total"] = len(findings)
    for band in ("VERIFIED", "PROBABLE", "UNVERIFIED"):
        result[band] = 0
    for finding in findings:
        tier = str(finding.get("risk_tier", "UNSCORED")).upper()
        result[tier if tier in result else "UNSCORED"] += 1
        band = finding.get("confidence_band")
        if band in result:
            result[band] += 1
    return result


def _violates_policy(findings: list[dict[str, Any]], threshold: str | None) -> bool:
    if threshold is None:
        return False
    max_rank = _TIER_ORDER[threshold]
    return any(_TIER_ORDER.get(str(item.get("risk_tier", "UNSCORED")).upper(), 4) <= max_rank for item in findings)


def _sync_bundle(bundle: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Send a signed bundle only through an explicit mutually authenticated TLS call."""
    if not args.sync_url.startswith("https://"):
        raise ValueError("--sync-url must use https://")
    if not args.client_cert or not args.client_key:
        raise ValueError("--sync-url requires both --client-cert and --client-key for mTLS")
    tls_context = ssl.create_default_context(cafile=args.ca_cert)
    tls_context.load_cert_chain(certfile=args.client_cert, keyfile=args.client_key)
    with httpx.Client(
        verify=tls_context,
        timeout=args.sync_timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        response = client.post(
            args.sync_url,
            json=bundle,
            headers={"X-ECDAT-Agent-ID": bundle["agent_id"], "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecdat",
        description="Offline cryptographic asset discovery with optional signed report delivery.",
    )
    parser.add_argument("target", type=Path, help="Local source file or directory to scan.")
    parser.add_argument("--json-out", metavar="PATH", help="Write full scored findings JSON to PATH.")
    parser.add_argument("--summary-only", action="store_true", help="Print only risk counts; never print finding paths.")
    parser.add_argument("--redact-paths", action="store_true", help="Redact paths not relative to the scanned target.")
    parser.add_argument(
        "--source-context", choices=("SOURCE", "TEST_ONLY", "DEMO_ONLY"),
        help="Declare the whole scan target's context; overrides path-based test/demo labeling.",
    )
    parser.add_argument(
        "--min-confidence",
        choices=("VERIFIED", "PROBABLE", "UNVERIFIED"),
        default=None,
        help="Drop findings whose confidence_band is below this level before printing. "
             "Independent of --fail-on.",
    )
    parser.add_argument("--fail-on", choices=("CRITICAL", "HIGH", "MEDIUM", "LOW"), help="Exit 2 when a finding meets or exceeds this tier.")
    parser.add_argument("--data-shelf-life-years", type=float, help="Explicit PQC/HNDL assumption applied to this scan.")
    parser.add_argument("--report-bundle", metavar="PATH", help="Write a signed bundle for later dashboard delivery.")
    parser.add_argument("--organization-id", help="Organization identifier required for --report-bundle.")
    parser.add_argument("--repository-id", help="Stable local repository identifier required for --report-bundle.")
    parser.add_argument("--agent-id", help="Provisioned local scanning-agent identifier required for --report-bundle.")
    parser.add_argument("--signing-key", metavar="PEM", help="Local Ed25519 PEM private key required for --report-bundle.")
    parser.add_argument("--sync-url", help="Explicit HTTPS report-ingestion endpoint; scanning never contacts it otherwise.")
    parser.add_argument("--client-cert", metavar="PEM", help="mTLS client certificate required with --sync-url.")
    parser.add_argument("--client-key", metavar="PEM", help="mTLS client private key required with --sync-url.")
    parser.add_argument("--ca-cert", metavar="PEM", help="Private CA bundle used to verify a dashboard ingestion endpoint.")
    parser.add_argument("--sync-timeout", type=float, default=15.0, help="Report-sync timeout in seconds (default: 15).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = args.target.resolve()
    if not target.exists():
        print(f"error: target does not exist: {target}", file=sys.stderr)
        return 1
    if args.data_shelf_life_years is not None and args.data_shelf_life_years < 0:
        print("error: --data-shelf-life-years must be non-negative", file=sys.stderr)
        return 1
    if args.sync_url and not args.report_bundle:
        print("error: --sync-url requires --report-bundle", file=sys.stderr)
        return 1

    findings = _prepare_findings(
        target, args.redact_paths, args.data_shelf_life_years, args.source_context
    )
    if args.min_confidence:
        from scanner.confidence import meets_band_threshold
        findings = [
            f for f in findings
            if meets_band_threshold(f.get("confidence_band", "UNVERIFIED") or "UNVERIFIED", args.min_confidence)
        ]
    summary = _summary(findings)

    result: dict[str, Any] = {"summary": summary, "findings": findings}

    if args.report_bundle:
        required = (args.organization_id, args.repository_id, args.agent_id, args.signing_key)
        if not all(required):
            print("error: --report-bundle requires --organization-id, --repository-id, --agent-id, and --signing-key", file=sys.stderr)
            return 1
        bundle = build_bundle(
            organization_id=args.organization_id,
            repository_id=args.repository_id,
            agent_id=args.agent_id,
            findings=findings,
            summary=summary,
            scan_context={
                "source_root": target.name,
                "path_redaction": args.redact_paths,
                "data_shelf_life_years": args.data_shelf_life_years,
                "source_context": args.source_context,
                "scanner_mode": "offline_local",
            },
        )
        signed = sign_bundle(bundle, load_private_key(args.signing_key))
        Path(args.report_bundle).write_text(json.dumps(signed, indent=2), encoding="utf-8")
        result["report_bundle"] = {
            "path": str(Path(args.report_bundle)),
            "digest": signed["bundle_digest"],
            "signature_algorithm": signed["signature_algorithm"],
        }
        if args.sync_url:
            try:
                result["sync"] = _sync_bundle(signed, args)
            except (ValueError, ssl.SSLError, httpx.HTTPError) as exc:
                print(f"error: report sync failed: {exc}", file=sys.stderr)
                return 1

    if args.summary_only:
        print(json.dumps({"summary": summary, "policy": args.fail_on}, indent=2))
    elif args.report_bundle:
        print(json.dumps(result, indent=2))
    else:
        # Preserve the established stdout contract used by scan_runner and
        # existing CI integrations: a JSON array of finding objects.
        print(json.dumps(findings, indent=2))
    if args.json_out:
        # Keep the legacy artifact contract: integrations receive a JSON array
        # of findings, while the signed report bundle holds richer metadata.
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    return 2 if _violates_policy(findings, args.fail_on) else 0



if __name__ == "__main__":
    raise SystemExit(main())
