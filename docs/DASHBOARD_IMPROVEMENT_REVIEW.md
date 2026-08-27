# ECDAT Dashboard: Professionalism and Usability Improvement Review

> **Scope boundary:** This is a design and product recommendation report only.
> No dashboard JSX, CSS, layout, scan-start control, or visual design was
> changed as part of this work. The existing dashboard remains mock-driven until
> a protected analyst API and tenant authorization are implemented.

## Current integration posture

The dashboard is currently a client-side mock presentation rather than a live,
authorized consumer of ECDAT reports. The correct next data flow is
read-only: an authenticated analyst reads server-persisted, organization-scoped
report records through the TLS gateway. It must never receive a shared backend
API key or initiate a local scan.

| Priority | Recommended improvement | Why it matters |
| --- | --- | --- |
| P0 | Replace mock data through a typed, read-only analyst API contract after RBAC/tenant isolation exist. | Prevents a polished UI from being mistaken for live security evidence. |
| P0 | Add explicit report provenance beside every analysis: report ID, agent ID, received time, bundle SHA-256 digest, signature status, model version, and `SOURCE`/`TEST_ONLY`/`DEMO_ONLY` context. | Lets a senior analyst judge custody and evidence quality before acting. |
| P0 | Show truth-preserving state design: empty, loading, permission denied, stale data, failed verification, and no-findings states. | Avoids silently substituting demo or stale data during security review. |
| P1 | Separate the hierarchy into portfolio, repository, scan, finding, and remediation detail routes/components. | The current monolithic dashboard logic will become difficult to test once live data and filters arrive. |
| P1 | Put the two risk axes side by side: **classically weak today** and **PQC/HNDL planning**. | Avoids treating a quantum-migration finding as an immediate exploited vulnerability. |
| P1 | Make risk filters include confidence, source context, owner, scan time, and policy threshold—not color alone. | Reduces false urgency and supports analyst triage. |
| P1 | Attach visible assumption cards to HNDL outcomes: shelf-life source, model version, threat-horizon assumption, and missing-context warning. | Makes PQC reporting reproducible and defensible. |
| P1 | Use server-generated export controls with report ID, digest, classification, retention warning, and audit event. | Avoids browser-only Blob exports that could omit custody metadata or leak sensitive data. |
| P2 | Add keyboard-complete tables, visible focus states, text labels in addition to color, high-contrast mode, and responsive small-screen drilldowns. | Improves accessibility and usability for long analyst sessions. |
| P2 | Establish component boundaries for query state, summary cards, finding table, provenance drawer, risk explanation, and export panel. | Makes integration testing and design changes safer than editing a single large view. |

## Suggested information architecture

Use a portfolio overview for organization-level counts and freshness; a
repository view for trend and ownership; a scan view for signed report
provenance; and a finding detail for evidence, deterministic risk rationale,
PQC assumptions, and remediation. Keep scan creation outside the dashboard.
The dashboard should present delivery status as an immutable event, not a
button that changes an engineer's source environment.

## Suggested analyst API contract

When identity and tenant authorization are ready, a read-only API should expose
only the authenticated analyst's organization: report list, repository list,
scan summary, scan findings, risk-assessment details, and CBOM export. Each
response should be non-cacheable and include request ID and custody fields.
The gateway can retain `/api/` as the same-origin prefix, but backend query
authorization must be implemented before that route is made public.

## Acceptance criteria before connecting live UI data

1. An unauthenticated browser cannot read report data.
2. An analyst cannot enumerate another organization's report, scan, or finding
   by changing an ID.
3. Every displayed finding shows its source context and analyst-relevant
   provenance.
4. The UI distinguishes signed accepted reports from failed or stale delivery.
5. Exports are server-created, authorized, classified, and audit logged.
6. Automated accessibility and responsive checks cover loading, empty, error,
   and populated states.
