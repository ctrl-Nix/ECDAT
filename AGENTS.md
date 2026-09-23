# AGENTS.md

Read automatically by every coding agent in this repository. Keep it short; it is loaded on every turn.

## What this project is

ECDAT — a local, Docker-packaged cryptographic discovery and CBOM tool. Python 3.11 / FastAPI / SQLAlchemy 2.0 / PostgreSQL 16 backend; React 18 + Vite + Tailwind dashboard in `dashboard/`.

**Not** Go. **Not** UUID primary keys. **Not** `/api/v1` routes. If you are about to write any of those, you have pattern-matched to a different project — stop and re-read.

## Read before writing code

1. Your assigned spec in `docs/` — in full, including its Section 11.
2. `SYSTEM_INTERFACE_CONTRACT.md` — §1 file ownership, §2 schema and migration numbers, §3 naming, §9 branch and commit rules, and every conflict ID your spec's Section 10 names.
3. `AGENT_RULES.md`.
4. Every path in your spec's Section 4.

Read nothing else. Do not crawl `node_modules/`, `package-lock.json`, `dashboard/` internals you do not own, or `tests/` outside your own test files. Reading the whole tree wastes the context you need for the actual work.

## Authority order

Spec Section 7 (literal interfaces) → `SYSTEM_INTERFACE_CONTRACT.md` → spec prose → your own judgement. Your judgement never wins. If two sources disagree, stop and report it. Do not pick one silently.

## The three rules agents break most

**1. Stay inside your file ownership.** Your spec's Section 5 lists what you may touch.
- `SOLE` to another feature — never open it, not even to read a symbol. Take the symbol from the contract or from that feature's spec.
- `FROZEN` (`api/services/scan_runner.py`, `api/services/risk_engine.py`, `scanner/finding.py`) — do not edit unless your spec explicitly owns that edit.
- `COORDINATED` — you may edit, but touch only the lines your feature needs and list every one in your final report.

**2. Migration numbers are assigned, not chosen.** Contract §2.1 allocates them. Never renumber, never invent, never reuse. Every schema change lands in **both** `db/schema.sql` and your numbered migration, plus a `docker-compose.yml` initdb mount, in the same commit.

**3. Stop rather than guess.** Check your spec's Section 11 first — most situations are answered there. If a situation is not covered, or a file you need does not exist because an earlier feature has not merged, **stop and report**. Do not stub it, do not fake a passing test, do not define a local substitute, do not widen your ownership. Stopping is the cheap failure; guessing is the expensive one.

## Project-specific constraints

- **Never use regex for source-code crypto detection.** Python uses the `ast` module; Java and JavaScript use tree-sitter with YAML rules.
- **Roles** are `Role` enum members from `api/core/rbac.py` (`SECURITY_ADMIN`, `AUDITOR`, `DEVELOPER`). Never a bare string. There is no `analyst` or `Admin` role.
- **Frontend colours** come only from the tokens in `dashboard/tailwind.config.js`. Never raw hex. Never numeric palette steps like `bg-green-100` — `green` is redefined as a single token value, so those classes render nothing at all.
- **Dependency versions:** do not add or change any version your spec's Section 6 does not introduce. Do not tighten an existing floor to `==`. The floors in contract §3.10 are correct.
- **Confidence bands** are `VERIFIED` / `PROBABLE` / `UNVERIFIED`. Inventory-grade evidence (a package present in an image) is `UNVERIFIED`, never `VERIFIED`. Never relabel weak evidence to get past a filter.
- **Scope:** source, dependency, config/IaC, binary and container scanning are all in scope. Registry pulls and runtime analysis are not, and must not be implied anywhere in code, UI, CLI or docs.

## Git

- Branch from `main`: `feat/<code-lowercase>-<slug>` — e.g. `feat/bin-binary-scanning`.
- Commit as `<CODE>: <imperative summary>` — e.g. `BIN: add ELF symbol table parser`.
- Never commit to `main`. Never force-push. Never touch another agent's branch.
- Rebase onto `main` before declaring done.

## Done means

Run your spec's Section 12 commands exactly as written and paste the real output into your final report. If a command fails, fix it or report it. Never edit a test to make it pass. Never delete a failing assertion.

Your final report must list: the spec implemented, Section 12 output, every `COORDINATED` file touched and why, anything blocked, and any deviation from the spec. "No deviations" is the expected answer.
