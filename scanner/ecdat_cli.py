"""Branded command wrapper for ECDAT's local scanner and report tools."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from api.services.cbom_generator import build_cbom_from_findings
from scanner import cli as scanner_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecdat",
        description="Local cryptographic discovery, CBOM generation, and signed report sync.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a local target.")
    scan_parser.add_argument("target", type=Path, nargs="?", help="Local file or directory to scan.")
    scan_parser.add_argument("--scan-type", action="append", choices=("source", "dependency", "config", "binary", "container"))
    scan_parser.add_argument("--image-tar", type=Path, metavar="PATH")
    scan_parser.add_argument("--min-confidence", choices=("VERIFIED", "PROBABLE", "UNVERIFIED"))
    scan_parser.add_argument("--json-out", metavar="PATH")
    scan_parser.add_argument("--summary-only", action="store_true")
    scan_parser.add_argument("--redact-paths", action="store_true")
    scan_parser.add_argument("--source-context", choices=("SOURCE", "TEST_ONLY", "DEMO_ONLY"))
    scan_parser.add_argument("--fail-on", choices=("CRITICAL", "HIGH", "MEDIUM", "LOW"))
    scan_parser.add_argument("--data-shelf-life-years", type=float)
    scan_parser.add_argument("--report-bundle", metavar="PATH")
    scan_parser.add_argument("--organization-id")
    scan_parser.add_argument("--repository-id")
    scan_parser.add_argument("--agent-id")
    scan_parser.add_argument("--signing-key", metavar="PEM")
    scan_parser.add_argument("--sync-url")
    scan_parser.add_argument("--client-cert", metavar="PEM")
    scan_parser.add_argument("--client-key", metavar="PEM")
    scan_parser.add_argument("--ca-cert", metavar="PEM")
    scan_parser.add_argument("--sync-timeout", type=float, default=15.0)
    scan_parser.set_defaults(handler=cmd_scan)

    cbom_parser = subparsers.add_parser("cbom", help="Generate a CBOM from scored JSON findings.")
    cbom_parser.add_argument("findings_json", type=Path)
    cbom_parser.add_argument("--summary", type=Path, required=True)
    cbom_parser.add_argument("--output", type=Path)
    cbom_parser.add_argument("--organization-id")
    cbom_parser.set_defaults(handler=cmd_cbom)

    sync_parser = subparsers.add_parser("sync", help="Send a signed report bundle to an HTTPS endpoint.")
    sync_parser.add_argument("bundle_json", type=Path)
    sync_parser.add_argument("--url", required=True)
    sync_parser.add_argument("--client-cert", required=True, metavar="PEM")
    sync_parser.add_argument("--client-key", required=True, metavar="PEM")
    sync_parser.add_argument("--ca-cert", metavar="PEM")
    sync_parser.add_argument("--timeout", type=float, default=15.0)
    sync_parser.set_defaults(handler=cmd_sync)

    return parser


def _append_option(argv: list[str], name: str, value: Any) -> None:
    if value is not None:
        argv.extend((name, str(value)))


def cmd_scan(args: argparse.Namespace) -> int:
    """Delegate to the existing scanner CLI without changing its contract."""
    scan_types = args.scan_type or []
    if args.image_tar is not None and "container" not in scan_types:
        print("error: --image-tar requires --scan-type container", file=sys.stderr)
        return 1
    if args.target is None and args.image_tar is None:
        print("error: scan requires a target or --image-tar", file=sys.stderr)
        return 1

    forwarded: list[str] = []
    if args.target is not None:
        forwarded.append(str(args.target))
    for scan_type in scan_types:
        forwarded.extend(("--scan-type", scan_type))
    _append_option(forwarded, "--image-tar", args.image_tar)
    _append_option(forwarded, "--min-confidence", args.min_confidence)
    _append_option(forwarded, "--json-out", args.json_out)
    for flag in ("--summary-only", "--redact-paths"):
        if getattr(args, flag[2:].replace("-", "_")):
            forwarded.append(flag)
    _append_option(forwarded, "--source-context", args.source_context)
    _append_option(forwarded, "--fail-on", args.fail_on)
    _append_option(forwarded, "--data-shelf-life-years", args.data_shelf_life_years)
    _append_option(forwarded, "--report-bundle", args.report_bundle)
    _append_option(forwarded, "--organization-id", args.organization_id)
    _append_option(forwarded, "--repository-id", args.repository_id)
    _append_option(forwarded, "--agent-id", args.agent_id)
    _append_option(forwarded, "--signing-key", args.signing_key)
    _append_option(forwarded, "--sync-url", args.sync_url)
    _append_option(forwarded, "--client-cert", args.client_cert)
    _append_option(forwarded, "--client-key", args.client_key)
    _append_option(forwarded, "--ca-cert", args.ca_cert)
    forwarded.extend(("--sync-timeout", str(args.sync_timeout)))
    return scanner_cli.main(forwarded)


def cmd_cbom(args: argparse.Namespace) -> int:
    """Build a DB-free CycloneDX document from JSON findings and summary."""
    try:
        findings = json.loads(args.findings_json.read_text(encoding="utf-8"))
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
        cbom = build_cbom_from_findings(
            findings,
            summary,
            organization_id=args.organization_id,
        )
        rendered = json.dumps(cbom, indent=2, ensure_ascii=False)
        if args.output is None:
            print(rendered)
        else:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"error: CBOM generation failed: {exc}", file=sys.stderr)
        return 1


def cmd_sync(args: argparse.Namespace) -> int:
    """POST an already-signed bundle over HTTPS with mutual TLS."""
    parsed = urlsplit(args.url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        print("error: --url must be a valid https:// URL", file=sys.stderr)
        return 1
    if args.timeout <= 0:
        print("error: --timeout must be greater than zero", file=sys.stderr)
        return 1

    try:
        bundle = json.loads(args.bundle_json.read_text(encoding="utf-8"))
        if not isinstance(bundle, dict) or not isinstance(bundle.get("agent_id"), str):
            raise ValueError("bundle must be an object containing agent_id")
        tls_context = ssl.create_default_context(cafile=str(args.ca_cert) if args.ca_cert else None)
        tls_context.load_cert_chain(certfile=str(args.client_cert), keyfile=str(args.client_key))
        with httpx.Client(
            verify=tls_context,
            timeout=args.timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = client.post(
                args.url,
                json=bundle,
                headers={"X-ECDAT-Agent-ID": bundle["agent_id"], "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ssl.SSLError, httpx.HTTPError) as exc:
        print(f"error: report sync failed: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, ssl.SSLError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
