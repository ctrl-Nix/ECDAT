# Deployment TLS Material

This directory is intentionally empty of certificate material. At deployment,
mount the following organization-issued files with permissions readable by the
unprivileged gateway container but not by other host users:

* `server.crt` — the public certificate chain for the dashboard hostname.
* `server.key` — the corresponding private key.
* `agent-ca.crt` — the CA certificate that issues scanning-agent client
  certificates; do not use a broad corporate root if a dedicated issuing CA is
  available.

These files are ignored by `.gitignore`. See `docs/SECURE_DEPLOYMENT.md` for
trust-boundary and rotation guidance.
