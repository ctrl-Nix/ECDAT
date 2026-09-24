# ECDAT CLI guide

Install the project from its root with `pip install -e .`. This installs the
`ecdat` command. The CLI scans local files and directories; it does not pull
container images from a registry or perform runtime analysis.

## Subcommands

### `ecdat scan <target>`

Scan a local file, directory, or supported artifact. Findings are written as a
JSON array to standard output unless `--summary-only` is selected. The command
returns `0` on success, `1` on an error, and `2` when `--fail-on` is exceeded.

```sh
ecdat scan ./src/
ecdat scan ./src/ --fail-on HIGH
ecdat scan ./src/ --json-out findings.json --redact-paths
ecdat scan ./project/ --scan-type source --scan-type dependency
ecdat scan ./image.tar --scan-type container --image-tar ./image.tar
```

Supported scan options:

- `--scan-type {source,dependency,config,binary,container}` may be repeated.
  If omitted, the scanner uses its default source scan.
- `--image-tar PATH` supplies a local OCI archive or image-layout path and
  requires `--scan-type container`.
- `--min-confidence {VERIFIED,PROBABLE,UNVERIFIED}` filters findings by the
  confidence band.
- `--json-out PATH`, `--summary-only`, `--redact-paths`, and
  `--source-context {SOURCE,TEST_ONLY,DEMO_ONLY}` control output and context.
- `--fail-on {CRITICAL,HIGH,MEDIUM,LOW}` returns exit code `2` when a finding
  reaches that risk tier.
- `--data-shelf-life-years FLOAT` supplies an explicit risk-scoring assumption.
- `--report-bundle PATH` writes a signed local report. It requires
  `--organization-id`, `--repository-id`, `--agent-id`, and `--signing-key`.
- `--sync-url HTTPS_URL` explicitly uploads the signed report. It requires
  `--report-bundle`, `--client-cert`, and `--client-key`; `--ca-cert` and
  `--sync-timeout` are optional.

### `ecdat cbom <findings-json> --summary <summary-json>`

Generate CycloneDX 1.6 CBOM JSON from already-scored finding and summary files.
This command needs no database connection.

```sh
ecdat cbom findings.json --summary summary.json
ecdat cbom findings.json --summary summary.json --output report.cdx.json
ecdat cbom findings.json --summary summary.json --organization-id org-42
```

Output goes to standard output unless `--output PATH` is provided. Findings
must include `file`, `line`, `library`, `algorithm`, `confidence`, `risk_tier`,
`risk_reason`, and `primitive`. The summary must contain `total`, `CRITICAL`,
`HIGH`, `MEDIUM`, `LOW`, and `UNSCORED` counts consistent with the findings.

### `ecdat sync <bundle-json> --url <https://...>`

Send an already-signed report bundle to an HTTPS endpoint using mutual TLS.
The command does not sign or change the bundle.

```sh
ecdat sync report-bundle.json \
  --url https://dashboard.example/agent/v1/report-bundles \
  --client-cert agent.crt \
  --client-key agent.key \
  --ca-cert dashboard-ca.pem
```

`--client-cert` and `--client-key` are required. `--ca-cert` is optional and
`--timeout` defaults to 15 seconds. Redirects are not followed. Only HTTPS
URLs are accepted; successful response JSON is printed to standard output.

## Docker

The image's default command continues to run the API with Uvicorn. To invoke
the installed CLI explicitly, replace that command:

```sh
docker run --rm -v "${PWD}:/target:ro" ecdat-scanner ecdat scan /target
```
