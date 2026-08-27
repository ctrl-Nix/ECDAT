# Secure Deployment Notes for ECDAT Report Synchronization

The provided Docker Compose file provides a **private local service topology**:
the database is not host-published, `data_net` and `app_net` are internal
networks, containers drop Linux capabilities, use `no-new-privileges`, and run
read-only with limited temporary filesystems. These settings protect the local
stack from accidental host exposure; they do not themselves make an internet
deployment complete.

For a dashboard available to senior analysts, deploy a dedicated TLS ingress or
API gateway in front of the backend. The supplied Nginx configuration reserves
`agent.ecdat.local` as a separate TLS virtual host for
`/agent/v1/report-bundles`; replace this placeholder with an organization-owned
ingestion hostname and a certificate valid for it. This virtual host uses
`ssl_verify_client on`, so client-certificate validation happens during the TLS
handshake. It then passes a trusted verification assertion only on the private
proxy-to-backend network. Do **not** host-publish the backend container when
`REPORT_SYNC_REQUIRE_MTLS=true`, because an internet caller could otherwise
forge the proxy assertion header.

The production database connection should use `POSTGRES_SSL_MODE=verify-full`
and `POSTGRES_SSL_ROOT_CERT=/run/secrets/postgres-ca.pem` for a remote managed
PostgreSQL service. The bundled local Compose service intentionally selects
`disable` only because it has no external listener and communicates over its
isolated Docker network. A production deployment should use a secret manager or
Docker/Kubernetes secret mounts for database credentials, API keys, client
certificate material, and the private agent signing key. None should appear in
an image layer, browser bundle, `.env.example`, repository, or CI log.

The dashboard must eventually authenticate analysts through an organization
identity provider and obtain only short-lived, scoped access tokens. Do not
expose a generic `X-API-Key` in JavaScript. Before connecting the unchanged
dashboard UI, add analyst RBAC plus organization-scoped queries to prevent one
tenant's reports, repository identifiers, or exports from being read by another.

Transport encryption should be paired with the Ed25519 bundle signature. TLS
confidentiality prevents in-transit inspection; client-certificate verification
authenticates the sending connection; the detached signature and stored digest
prove the accepted payload came from the enrolled agent and was unchanged.

## Database initialization and upgrade procedure

For a **new** database volume, Compose mounts `db/schema.sql` followed by
`db/migrations/001_secure_reporting.sql` directly into PostgreSQL's init
directory. PostgreSQL does not recursively run SQL mounted under a subdirectory,
so this direct mount is intentional and has been validated against a fresh
PostgreSQL 16 container.

For an **existing** database, back up first, schedule maintenance, then run the
versioned migration exactly once using a role that can alter the ECDAT schema:

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 < db/migrations/001_secure_reporting.sql
```

Record the migration version in the operator change log. This repository does
not yet provide a full migration-history runner; do not rely on a container
restart to update an existing PostgreSQL data volume.

## Remaining production prerequisites

The implementation validates a signed agent bundle and a real mTLS path, but it
is not a production certification. Before public dashboard launch, implement
managed agent enrollment/revocation (rather than static environment mapping),
analyst SSO/RBAC, organization-scoped object authorization, durable audit-event
storage, rate limiting/WAF policy, backup/restore tests, certificate rotation,
and a security review of the deployed gateway. Keep report bundles and source
paths classified according to the organization's data-handling policy.

OWASP recommends TLS for sensitive data in transit and explicit authorization
checks for API object access.[1] These controls are prerequisites for a public
dashboard, not optional hardening.

## Reference

[1]: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html "OWASP Transport Layer Security Cheat Sheet"
