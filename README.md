# ECDAT — Enterprise Cryptographic Discovery & Analysis Tool
### PS 26164 — SIH 2026, Blockchain & Cybersecurity track (KIIT Internal Round)

An AST-based scanner that discovers cryptographic usage in Python source
code, generates a CycloneDX-format Cryptography Bill of Materials (CBOM),
scores each finding's exposure to future quantum attacks using an
explainable, rule-based model, recommends a purpose-aware PQC/hybrid
migration path, and blocks CI merges on policy-violating (deprecated/weak)
cryptography.

## What this is (and isn't)
- **Core product:** CLI scanner + GitHub Actions compliance gate.
- **Reporting layer:** React dashboard visualizing scan results, CBOM, and
  risk scores — engineer detail view and a decision-maker summary view.
- **Scope for this build:** Python source-code scanning only. Binary/
  container/library scanning is architecturally extensible but **not
  implemented** in this version — don't imply otherwise in the demo.
- **Risk scoring:** rule-based and explainable (see
  `skills/cbom-quantum-risk/SKILL.md`), never a black-box AI score.
- **Remediation text:** sourced from a fixed lookup table; an LLM may
  rephrase it for readability but never invents the fix (see
  `skills/remediation-copy/SKILL.md`).

## Quick start
```bash
git clone <repo-url>
cd ecdat
cp .env.example .env   # fill in your DB connection string, no secrets committed
docker compose up
```

## Running a scan
```bash
python -m scanner.cli scan ./path-to-target-repo
```

## Project structure
```
ecdat/
├── scanner/              # AST-based crypto detection engine
├── backend/               # FastAPI app
├── frontend/               # React dashboard
├── skills/                  # Agent skill definitions
│   ├── ast-crypto-scanning/
│   ├── cbom-quantum-risk/
│   ├── remediation-copy/
│   ├── secure-api-development/
│   └── ci-cd-gate/
├── .github/workflows/     # CI/CD compliance gate
├── ARCHITECTURE.md
├── .clinerules
└── AGENTS_AND_SKILLS.md
```

## Team
| Person | Owns |
|---|---|
| Shashank | Scanner core & CI/CD gate |
| Ronak | Database |
| Shreyanshi | Remediation copy (+ shared backend) |
| Shreyanshi, Ronak, Shashank | Backend (shared) |
| Karan | Packaging |
| Karan & Satyam | Frontend |
| Maitreyi | Report format, CBOM/risk-score co-design, presentation |

## Status
Working build — see `ARCHITECTURE.md` for current scope and
`AGENTS_AND_SKILLS.md` for agent/skill documentation.

## Demo line (say this, verbatim, on stage)
> "We scan code structurally — not with regex — to build a standardized
> CBOM, score every finding for quantum risk using a documented, explainable
> formula, and block merges that introduce dangerous crypto, mapped to DPDP
> and NIST guidance."

Never say "zero false positives." Say "minimized through AST
context-awareness."
