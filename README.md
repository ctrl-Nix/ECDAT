# ECDAT — Enterprise Cryptographic Discovery & Quantum-Risk Analysis Platform

SIH 2026 · PS 26164 · Team **ctrl-Nix** (KIIT Bhubaneswar)

Scans code for weak / at-risk cryptography, builds a standardized **CBOM**
(CycloneDX), scores each finding's quantum risk (Mosca's algorithm), recommends
a fix, and blocks merges that introduce dangerous crypto via a CI/CD gate.

> We scan code **structurally (AST, not regex)** to build a standardized CBOM,
> score every finding for quantum risk, and block merges that introduce
> dangerous crypto — mapped to DPDP and NIST guidance.

## Repository layout

```
scanner/            # AST-based crypto detection engine   (Shashank)
backend/            # FastAPI app + database layer         (backend trio)
  └── db/           #   schema, models, crud, tests        (Ronak)
frontend/           # React reporting dashboard            (Karan, Satyam)
skills/             # Agent skill definitions
.github/workflows/  # CI/CD compliance gate
ARCHITECTURE.md     # stack + data model + API routes (survival-gate item)
.clinerules         # agent rules (survival-gate item)
AGENTS_AND_SKILLS.md
```

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the data model and API routes.

## Quick start (database layer)

```bash
docker compose up -d          # Postgres, schema applied automatically
pip install -r requirements.txt
python -m pytest              # DB tests (run on SQLite, no Docker needed)
```

Details for the DB lane: **[backend/db/README.md](backend/db/README.md)**.
