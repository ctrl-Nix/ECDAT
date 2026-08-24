# PROMPT: Fix ECDAT Architecture & Create Placeholders

You are the architecture fix agent for ECDAT. Your job is to clean up the codebase structure, update documentation, create empty placeholder files for missing components, and ensure the architecture is documented correctly.

## STEP 1: Clean Up Stray Files at Root

Move these files into the `docs/` folder (create docs/ if it doesn't exist):
- CHUNK_1_MOVE_FILES.md → docs/CHUNK_1_MOVE_FILES.md
- PROMPT_RESTRUCTURE_AGENT.md → docs/PROMPT_RESTRUCTURE_AGENT.md
- SKILL_GENERATE_AUDIT.md → docs/SKILL_GENERATE_AUDIT.md
- SKILL_SCANNER_FIXES.md → docs/SKILL_SCANNER_FIXES.md
- RISK_ENGINE_SPEC.md → docs/RISK_ENGINE_SPEC.md
- clinerules.txt → docs/clinerules.txt

If any of these files don't exist, skip them.

## STEP 2: Create Placeholder Files (Empty — Do Not Write Code)

Create these files with EMPTY content (just a comment header):

```python
# api/core/config.py
"""ECDAT API configuration."""
# TODO: Implement pydantic-settings for env vars
```

```python
# api/core/security.py
"""API security — API key validation."""
# TODO: Implement X-API-Key header validation
```

```python
# api/routers/scans.py
"""Scan router — POST /scans, GET /scans/{id}."""
# TODO: Implement scan creation and retrieval endpoints
```

```python
# api/routers/findings.py
"""Findings router — GET /scans/{id}/findings."""
# TODO: Implement paginated findings endpoint
```

```python
# api/routers/cbom.py
"""CBOM router — GET /scans/{id}/cbom."""
# TODO: Implement CycloneDX CBOM export endpoint
```

```python
# api/services/scan_runner.py
"""Scan runner — bridges scanner CLI to database."""
# TODO: Implement subprocess call to scanner.cli + findings ingestion
```

```python
# api/services/cbom_generator.py
"""CBOM generator — transforms findings to CycloneDX JSON."""
# TODO: Implement CycloneDX 1.6 cryptographic-asset transform
```

```python
# api/services/risk_engine.py
"""Risk engine — rule-based quantum-aware risk scoring."""
# TODO: Implement RISK_RULES dict + key_size override + Mosca assessment
```

```javascript
// dashboard/src/api.js
// TODO: Implement axios client with baseURL and X-API-Key header
```

```javascript
// dashboard/src/components/StatCards.jsx
// TODO: Implement 4 summary stat cards
```

```javascript
// dashboard/src/components/ChartsPanel.jsx
// TODO: Implement Recharts BarChart + PieChart
```

```javascript
// dashboard/src/components/RiskBadge.jsx
// TODO: Implement colored risk tier badge
```

```javascript
// dashboard/src/components/ConfidenceStamp.jsx
// TODO: Implement shield icon + verified/unverified stamp
```

```javascript
// dashboard/src/components/CbomExport.jsx
// TODO: Implement CBOM download button
```

```python
# scripts/generate_demo_repo.py
"""Demo repo generator — creates mock enterprise codebase."""
# TODO: Implement multi-language demo repo with intentional crypto flaws
```

```yaml
# .github/workflows/ecdat-scan.yml
# TODO: Implement GitHub Actions CI/CD gate workflow
```

## STEP 3: Update ARCHITECTURE.md

Replace the entire ARCHITECTURE.md file with the content from the file at this path: docs/ARCHITECTURE.md (if it exists there) or use the updated version that reflects:

1. Current directory structure with all files marked as either:
   - ✅ Built (existing working code)
   - 🚧 Placeholder (empty file created in Step 2)
   - ❌ Not started (not even a placeholder yet)

2. Component contracts section (scanner → API → dashboard data flow)
3. Technology stack table
4. Security posture summary
5. Work assignment table showing who owns what and current status

The updated ARCHITECTURE.md must be the single source of truth for the entire team.

## STEP 4: Update skills/backend/SKILL.md

Replace the entire skills/backend/SKILL.md file with comprehensive backend engineer guidance. It must include:

- Territory: api/ directory structure
- Rules: FastAPI only, Pydantic v2, SQLAlchemy 2.0, APIRouter pattern, thin routers, business logic in services/, never accept raw shell commands, background tasks for scans, never leak tracebacks, API key auth, CBOM on demand
- Reference pattern: study api/routers/remediation.py as the working example
- Endpoint specification table (POST /scans, GET /scans/{id}, GET /scans/{id}/findings, GET /scans/{id}/cbom, GET /scans/{id}/risk-summary, GET /health)
- Pydantic model pattern with from_attributes=True
- Scan runner service pattern (subprocess, path validation, parse findings.json)
- Router pattern for POST /scans (202 Accepted, background task)
- Database CRUD functions available in db/crud.py
- Error response pattern (sanitized, no raw exceptions)
- What NOT to do table
- Testing commands
- Definition of done checklist

## STEP 5: Update AGENTS_AND_SKILLS.md

Ensure it is a clean registry table:

| Skill | Owner | Path | Status |
|---|---|---|---|
| Database | Ronak | skills/db/SKILL.md | Active |
| Backend API | Shreyanshi | skills/backend/SKILL.md | Active |
| Frontend | Karan + Satyam | skills/frontend/SKILL.md | Active |
| Scanner | Shashank | skills/scanner/SKILL.md | Active |
| CBOM + Quantum Risk | Maitreyi | skills/cbom-quantum-risk/SKILL.md | Active |
| CI/CD Gate | Shashank | skills/ci-cd-gate/SKILL.md | Active |
| Remediation Copy | Shreyanshi | skills/remediation-copy/SKILL.md | Active |

Remove any placeholder text like "[fill in...]".

## STEP 6: Verify Structure

After all changes, verify:
- [ ] No stray .md files at repo root (all moved to docs/)
- [ ] api/core/config.py exists (even if empty)
- [ ] api/core/security.py exists (even if empty)
- [ ] api/routers/scans.py exists (even if empty)
- [ ] api/routers/findings.py exists (even if empty)
- [ ] api/routers/cbom.py exists (even if empty)
- [ ] api/services/scan_runner.py exists (even if empty)
- [ ] api/services/cbom_generator.py exists (even if empty)
- [ ] api/services/risk_engine.py exists (even if empty)
- [ ] dashboard/src/api.js exists (even if empty)
- [ ] dashboard/src/components/StatCards.jsx exists (even if empty)
- [ ] dashboard/src/components/ChartsPanel.jsx exists (even if empty)
- [ ] dashboard/src/components/RiskBadge.jsx exists (even if empty)
- [ ] dashboard/src/components/ConfidenceStamp.jsx exists (even if empty)
- [ ] dashboard/src/components/CbomExport.jsx exists (even if empty)
- [ ] scripts/generate_demo_repo.py exists (even if empty)
- [ ] .github/workflows/ecdat-scan.yml exists (even if empty)
- [ ] ARCHITECTURE.md is updated and accurate
- [ ] skills/backend/SKILL.md is comprehensive
- [ ] AGENTS_AND_SKILLS.md is clean

## STEP 7: Final Report

List:
1. Every file moved to docs/
2. Every placeholder file created
3. Every file updated (ARCHITECTURE.md, SKILL.md, AGENTS_AND_SKILLS.md)
4. Current directory tree (top 3 levels)
5. Any issues encountered

Report back: "Architecture fix complete. Placeholders created. Documentation updated."
