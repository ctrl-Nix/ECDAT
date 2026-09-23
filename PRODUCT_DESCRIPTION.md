# ECDAT — Product Description & Pitch Context
## Enterprise Cryptographic Discovery & Analysis Tool
### Smart India Hackathon 2026 · PS 26164 · Team ctrl-Nix

---

## 1. The Problem (30 Seconds)

**Enterprises don't know where their vulnerable cryptography lives.**

- NIST's post-quantum cryptography (PQC) migration deadlines are approaching. Companies know they need to migrate.
- **But they can't migrate what they can't find.** Most enterprises have zero automated inventory of cryptographic usage across their codebases.
- **CBOM (Cryptography Bill of Materials)** was only standardized in CycloneDX v1.6 (April 2024). The tooling ecosystem is practically nonexistent.
- Current "solutions" are manual audits, regex-based scanners with high false positives, or SaaS products that require handing your source code to a third party.
- **The gap:** There is no open-source, self-hosted, CI/CD-integrated tool that discovers cryptographic usage, scores quantum risk, and produces a standardized CBOM.

**Judge hook:** *"Companies already know PQC migration is coming. What most of them don't have is an accurate, automated inventory of where their vulnerable cryptography actually lives — which is exactly why NIST and the CycloneDX standards body only formalized a machine-readable format for this in the last two years."*

---

## 2. The Solution: ECDAT (45 Seconds)

**ECDAT is a CLI-first, Docker-packaged cryptographic scanner that integrates into any enterprise CI/CD pipeline to catch weak cryptography before it reaches production.**

### What ECDAT Does (The 5 Requirements from PS 26164)

| Requirement | What ECDAT Delivers |
|---|---|
| **Discovery** | Scans Python, Java, JavaScript source code using AST analysis (not regex) |
| **Identification** | Detects algorithms, key sizes, protocols, libraries with confidence scoring |
| **Cataloguing (CBOM)** | Exports findings as CycloneDX 1.6 `cryptographic-asset` JSON |
| **Quantum-risk scoring** | Rule-based risk tiers (Critical/High/Medium/Low) with Mosca's theorem adaptation |
| **Recommendation & reporting** | Suggests PQC/classical replacements per finding; dashboard + CI summary |

### Two Deployment Modes, One Docker Image

```
Mode 1: CI/CD Gate                    Mode 2: Local/Legacy Scan
───────────────────                   ─────────────────────────
Enterprise CI pipeline                Engineer workstation
    │                                     │
    ▼                                     ▼
┌─────────────┐                    ┌─────────────┐
│ docker run  │                    │ docker run  │
│ ecdat-scan  │                    │ ecdat-scan  │
│ /workspace  │                    │ /path/to/code
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       ▼                                  ▼
  pass/fail summary                   findings.json
  + artifact upload                   + dashboard view
```

**Key principle:** Data never leaves the enterprise's infrastructure. No SaaS, no crawling GitHub URLs, no third-party data egress.

---

## 3. Technical Architecture (60 Seconds)

### Scanner Core (Built & Tested)
- **Python engine:** stdlib `ast` module — tracks import aliases, inspects Call/Import nodes only, immune to decoys (verified: comments and variable names containing "MD5" produce zero findings)
- **Java/JavaScript engine:** Tree-sitter with externalized YAML rules — adding a new language means writing a YAML file, not new scanner logic
- **Confidence scoring:** "high" only if import origin is verified; "unverified" if the object name matches but the import cannot be proven
- **18 findings** verified across 10 test fixtures (5 Python, 2 Java, 3 JavaScript) including adversarial negative tests

### Backend (FastAPI + PostgreSQL)
- Self-hosted via Docker Compose — scanner, database, API, and dashboard run on the enterprise's own network
- `findings` table stores evidence; `risk_assessments` table stores interpretation (separation allows risk models to be recomputed without touching scan history)
- Background task architecture: `POST /scans` returns 202 immediately, scan runs asynchronously

### Dashboard (React + Recharts)
- "Security audit ledger" aesthetic — dark theme, monospace for code, shield icons for confidence
- Real-time findings table, Recharts bar/donut charts, risk tier badges, CBOM export button
- Polls scan status every 3 seconds

### Risk Engine (Rule-Based, Not ML)
- **Two independent axes:** Classical security (is it broken now?) vs. Quantum vulnerability (will quantum computers break it?)
- MD5/SHA-1/DES = **Critical**, classically broken, NOT quantum-relevant
- RSA/ECC = **High**, quantum-vulnerable via Shor's algorithm
- AES-256 = **Low**, secure against both
- Key-size overrides: RSA-1024 bumps from High to Critical

---

## 4. What Makes ECDAT Different (The "So What?")

| Other Approaches | ECDAT |
|---|---|
| Regex-based scanners | **AST-based** — context-aware, decoy-immune |
| SaaS products that crawl your repo | **Self-hosted** — code never leaves your network |
| Manual crypto audits | **Automated** — runs on every PR via CI/CD gate |
| Generic vulnerability scanners | **Crypto-specific** — understands algorithms, primitives, key sizes |
| Proprietary report formats | **CycloneDX 1.6 CBOM** — industry-standard, machine-readable |
| "AI-powered" black-box risk scores | **Documented, rule-based** scoring — auditable, deterministic |

**Judge-ready line:** *"IBM's CBOMkit splits source-code detection and binary/container detection into separate tools because they are genuinely different techniques. We built them as separate engines behind one Finding contract — four detectors, one schema, one risk model. The confidence band tells you which technique produced each finding, so we never launder a package listing into the same certainty as a traced call site."*

---

## 5. Honest Build Status (Don't Oversell)

| Component | Status | Pitch Line |
|---|---|---|
| Multi-language scanner (Python/Java/JS) | ✅ Built & tested | "Our scanner detects crypto across three languages using AST analysis" |
| Unified Finding schema + confidence scoring | ✅ Built & tested | "Every finding carries a confidence score — 'high' means we verified the import" |
| PostgreSQL database + CRUD layer | ✅ Built & tested | "Findings are persisted with full audit history" |
| FastAPI app factory + remediation router | ✅ Built | "Our API is built on FastAPI with Pydantic validation" |
| Scan router + findings router | ✅ Built & tested | "The scan ingestion pipeline validates paths and persists findings asynchronously" |
| Risk engine + CBOM generator | ✅ Built & tested | "The deterministic risk engine computes quantum risk tiers and generates CycloneDX 1.6 CBOM" |
| Dashboard (React + Recharts + Vite) | ✅ Built (Demo Mode) | "Interactive visualization dashboard with trend charts, risk breakdowns, and CBOM viewer" |
| CI/CD gate workflow | ✅ Built & tested | "GitHub Actions workflow enforces `--fail-on HIGH` policy and blocks non-compliant PR merges" |
| Binary scanning (heuristic, ELF/PE/Mach-O) | 🚧 In this sprint | "Symbol-table and linked-library evidence. We report linkage, not proof of use — that distinction is in the confidence band" |
| Container image scanning (tarball / OCI layout) | 🚧 In this sprint | "Offline layer inspection: certificates parsed for real key sizes, plus OS and language package inventory. We never mount the Docker socket" |
| Third-party dependency scanning | 🚧 In this sprint | "Manifest and lockfile inventory for Python, Node and Java, normalised into the same Finding contract" |
| Config/IaC crypto scanning | 🚧 In this sprint | "TLS versions, weak ciphers and disabled verification in Kubernetes, Compose, Terraform, Nginx and CI config" |
| Registry pulls (`ecdat scan nginx:latest`) | ❌ Out of scope | "Deliberately offline. A registry pull would break the self-hosted, no-egress guarantee that is the point of the tool" |
| Runtime / dynamic analysis | ❌ Out of scope | "Every finding is static evidence. We never claim a finding executes" |

**Critical honesty rule:** Never claim "zero false positives." Say: *"False positives are minimized through AST context-awareness."*

---

## 6. Demo Script (5 Minutes)

### Minute 1: The Setup
> "This is Acme Bank — a realistic enterprise with legacy microservices in Python, Java, and JavaScript. They know PQC migration is coming, but they have no idea where their RSA-1024, MD5, and DES calls are hiding."

### Minute 2: The Scan
> "We run ECDAT against their codebase. In 15 seconds, it finds 18 cryptographic calls across three languages. Notice the confidence scoring — this MD5 finding is 'high' because we verified the `hashlib` import, not just matched a string."

### Minute 3: The Dashboard
> "Findings flow into the dashboard in real time. We see 7 weak-by-default algorithms, 1 unverified confidence finding, and the breakdown by language. The risk tier column shows Critical for MD5 — not because of quantum computers, but because collision attacks cost under $100."

### Minute 4: The CBOM Export
> "We export a CycloneDX 1.6 CBOM — the same standard IBM and the US government are standardizing on. This is machine-readable, not a PDF report. It goes straight into their compliance pipeline."

### Minute 5: The CI/CD Gate
> "Finally, we show the CI gate. A developer opens a PR with new MD5 code. The scanner runs automatically, fails the build, and prints only a summary to the public log — full details go to the authenticated dashboard. Weak crypto never reaches production."

---

## 7. Key Talking Points for Judges

### On Quantum Risk
- *"MD5 and SHA-1 are already broken by classical attacks — this isn't about quantum computers. RSA and ECC are the ones that quantum computers will actually break via Shor's algorithm. We keep these axes separate because conflating them is a common and damaging mistake."*

### On CBOM Standards
- *"CycloneDX only introduced cryptographic-asset support in v1.6, April 2024. NIST SP 1800-38B frames cryptographic inventorying as a foundational PQC-readiness practice. We're building the tooling for a standard that is literally two years old."*

### On Self-Hosting
- *"We treat our findings data with the same rigor we're asking enterprises to apply to their own cryptography. Findings require authentication to read, and our CI logs only ever expose a pass/fail summary publicly, never per-finding detail."*

### On Scope Discipline
- *"We run five detection engines — source AST, dependency manifests, config/IaC, binaries and container layers — and every one of them emits the same `Finding` contract, so the risk engine, CBOM generator and dashboard never learned about the new inputs. That is the architectural claim, and it is the reason adding four engines did not become four forks of the pipeline."*
- *"What we deliberately did not do is pretend they carry equal weight. A traced call site in Python source is `VERIFIED`. An `openssl` package present in a container image is `UNVERIFIED` — it proves the library is installed, not that RSA-1024 is used. Both are stored, both are exported, and the band travels with the finding into the CBOM. Collapsing that distinction is how scanners get a reputation for noise."*
- *"Still out of scope on purpose: registry pulls and any runtime analysis. Both would break the no-egress guarantee or claim something static evidence cannot support."*

### On False Positives
- *"We don't claim zero false positives — we claim they're minimized through AST context-awareness. Our negative tests prove it: a comment containing 'MD5' and a variable named `legacy_hash_unused` produce exactly zero findings."*

---

## 8. Team & Roles

| Member | Role | Contribution |
|---|---|---|
| Shashank (Lead) | Scanner core + CI/CD | AST engines, CLI, test fixtures, confidence scoring |
| Ronak | Database | PostgreSQL schema, CRUD layer, Docker Compose DB |
| Shreyanshi | Backend + Remediation | FastAPI routers, scan ingestion, LLM remediation copy |
| Karan | Packaging + Frontend | Dockerfile, docker-compose.yml, dashboard components |
| Satyam | Frontend + Testing | React dashboard, Recharts, Playwright E2E tests |
| Maitreyi | CBOM + Risk + Pitch | CycloneDX format, quantum-risk scoring, presentation |

---

## 9. One-Line Elevator Pitches

**For technical judges:**
> "ECDAT is a CLI-first cryptographic scanner that produces CycloneDX CBOMs and quantum-risk scores, self-hosted via Docker so your code never leaves your network."

**For business judges:**
> "We give enterprises an automated inventory of their cryptographic weaknesses before quantum computers make them critical — and we block new weak crypto from entering production via CI/CD gates."

**For the problem statement:**
> "ECDAT discovers, identifies, catalogues, scores, and recommends replacements for enterprise cryptography — across source code, with standardized CBOM output and quantum-aware risk classification."

---

## 10. DPDP / NIST Compliance Angle

**DPDP Act 2023 (India):**
- Section 8(a) — "reasonable security safeguards" — ECDAT identifies weak crypto that violates this
- Section 12 — data breach notification — weak MD5/SHA-1 password hashing is a pre-breach condition

**NIST Framework:**
- NIST SP 800-57 — key management guidance — ECDAT flags insufficient key sizes
- NIST SP 1800-38B — cryptographic inventorying for PQC readiness — ECDAT produces exactly this inventory
- NIST Post-Quantum Cryptography Standardization (2024) — ECDAT maps findings to PQC migration paths

**Pitch line:** *"DPDP requires 'reasonable security safeguards.' NIST requires cryptographic inventorying for PQC readiness. ECDAT does both — it tells you where your weak crypto lives and what to replace it with."*

---

## 11. Visuals for the PPT

Suggested slides:
1. **Title:** ECDAT — Enterprise Cryptographic Discovery & Analysis Tool
2. **The Problem:** The PQC migration gap + zero inventory
3. **The Solution:** Two-deployment-mode diagram (CI gate + local scan)
4. **Architecture:** Scanner → API → DB → Dashboard flow diagram
5. **Scanner Demo:** Screenshot of CLI output with findings
6. **Dashboard:** Screenshot of findings table + charts
7. **Risk Engine:** Two-axis diagram (classical vs. quantum)
8. **CBOM Export:** Sample CycloneDX JSON snippet
9. **CI/CD Gate:** GitHub Actions workflow diagram
10. **Team & Roadmap:** What we built vs. what's next
11. **Impact:** DPDP/NIST compliance angle
12. **Thank You / Q&A**

---

*This document is the single source of truth for ECDAT's product positioning. Use it to generate pitch decks, demo scripts, judge Q&A prep, and team alignment.*
