# Config & IaC Scanning Scope

Config and Infrastructure-as-Code (IaC) scanning (`--scan-type config`) discovers cryptographic declarations and weaknesses in structured configuration manifests.

## Supported Formats
- **Kubernetes / Docker Compose (YAML):** Ingress TLS declarations, ConfigMaps, service manifests, compose service settings
- **Terraform / OpenTofu (HCL2):** `tls_private_key`, `aws_lb_listener`, SSL policies, provider configs (`.tf` files)
- **Nginx Config:** `ssl_protocols`, `ssl_ciphers`, `ssl_verify_client` directives in `nginx.conf` and `*.conf`
- **CI/CD Pipelines (YAML):** GitHub Actions workflows (`.github/workflows/*.yml`), GitLab CI (`.gitlab-ci.yml`)
- **Generic JSON:** Structured TLS/crypto JSON configuration files (`*.json`)

## Detected Cryptographic Signals
- **TLS Versions:** Deprecated TLS 1.0 (`TLSv1.0`), TLS 1.1 (`TLSv1.1`), Quantum-vulnerable TLS 1.2 (`TLSv1.2`), Standard TLS 1.3 (`TLSv1.3`)
- **Weak Cipher Suites:** RC4, DES, 3DES, MD5-based ciphers, Export-grade ciphers
- **Key Sizes:** RSA key sizes (`rsa_bits` = 1024, 2048, 4096)
- **Certificate Verification Flags:** Insecure configurations such as `verify: false`, `insecure: true`, `ssl_verify: off`
- **Plaintext / Insecure Protocols:** Unencrypted protocol indicators

## Structural Detection (No Regex)
Detection is entirely structural:
- YAML documents are parsed via PyYAML and traversed by key-value paths.
- Terraform files are parsed via `python-hcl2` into structured AST objects.
- Nginx files are tokenized into directive-value pairs, ignoring comments and formatting.
- JSON files are parsed into native Python objects.

Comments and variable names that mention crypto terms (e.g., `# ssl_ciphers: RC4` or `old_tls_disabled: true`) do not trigger findings.

## Variable Interpolation & Confidence
- **Explicit Literals:** Emit `confidence: "high"`, `confidence_band: "VERIFIED"` (score 0.95)
- **Unresolved Variables / Interpolations:** Values containing `${VAR}`, `{{ var }}`, or `${{ secrets.* }}` are honestly reported with `confidence: "unverified"`, `confidence_band: "UNVERIFIED"` (score 0.35)

## Line Numbers
For parsed tree formats (YAML, HCL2, JSON), `line` is set to `0` (rendered as `—` in UI). For tokenized Nginx directives, the 1-based directive line number is recorded.

## What This Feature Is Not
- **Not a dynamic IaC evaluator:** Does not execute Terraform or validate live Kubernetes cluster state.
- **Not a general IaC security scanner:** Focuses strictly on cryptographic attack surface and configuration weaknesses.
- **Not a live container auditor:** Scans static repository files, not live container runtime settings.
