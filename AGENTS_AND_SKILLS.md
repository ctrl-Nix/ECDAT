# Agents & Skills Catalog — ECDAT

This document catalogs the custom AI agents and skills used to build this
project, as required by the judging non-negotiables. Fill in the bracketed
sections as the build actually happens — judges reward evidence of a real
iterative process over a speculative file nobody ever updated.

## Custom Agent

**Name:** [fill in, e.g. "Crypto Scanner Dev Agent"]
**Tool:** Cline / Roo Code (VS Code extension)
**Backend model:** [e.g. NVIDIA Build — Qwen2.5-Coder / Gemini Flash for planning]
**Role:** Implements and extends the AST-based crypto scanner, CBOM pipeline,
and remediation copy under `.clinerules` constraints, with mandatory human
review of every diff before merge.
**Guardrails:** Cannot use regex for scanning, cannot fabricate findings,
cannot commit secrets, cannot claim zero false positives, cannot output an
unexplained risk score, cannot use legal-conclusion language ("DPDP violation").

## Custom Skills

| Skill | Location | Purpose | Owner |
|---|---|---|---|
| ast-crypto-scanning | `skills/ast-crypto-scanning/SKILL.md` | Detect crypto usage structurally via `ast` | Shashank |
| cbom-quantum-risk | `skills/cbom-quantum-risk/SKILL.md` | Generate CBOM + score quantum exposure (explainable, purpose-aware) | Maitreyi & Shashank |
| remediation-copy | `skills/remediation-copy/SKILL.md` | Turn a finding into trustworthy remediation text | Shreyanshi |
| secure-api-development | `skills/secure-api-development/SKILL.md` | Build/modify FastAPI endpoints safely | Shreyanshi, Ronak, Shashank |
| ci-cd-gate | `skills/ci-cd-gate/SKILL.md` | Define and maintain the CI policy gate | Shashank |

## How these were used

[Fill in during/after the build — 2-3 sentences per skill on what mistake or
repeated pattern led to creating/tightening it, and roughly how many times the
agent invoked it. Example prompt for yourself: "The agent tried regex once on
Day 1, we corrected it in `.clinerules`, and it never happened again — that's
the story, write it down when it happens."]

- **ast-crypto-scanning:** [ ]
- **cbom-quantum-risk:** [ ]
- **remediation-copy:** [ ]
- **secure-api-development:** [ ]
- **ci-cd-gate:** [ ]
