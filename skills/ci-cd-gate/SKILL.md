# Skill: CI/CD Compliance Gate

## Purpose
Define and maintain the GitHub Actions workflow that runs the scanner on
every PR and fails the build when a policy-violating finding is detected —
this is the core "compliance instrument" narrative for the demo, and the
single highest-leverage 30-second moment in the pitch.

## When to use this skill
Any time the CI workflow is created, modified, or debugged.

## Required behavior
1. Workflow triggers on every `push` and `pull_request`.
2. Runs the AST scanner against the changed/full codebase.
3. Fails the workflow (non-zero exit code) if any finding meets the "policy
   violation" threshold — currently: MD5, SHA-1, RC4, DES, RSA < 2048
   detected — this must produce a visible red X on the PR, not just a
   warning in logs.
4. Also runs the negative-fixture test set from `ast-crypto-scanning/SKILL.md`
   as part of the same job — a workflow that only checks positives isn't
   proving the false-positive story, it's just proving detection works.
5. Uploads the scan report / CBOM as a workflow artifact regardless of
   pass/fail, so a judge can download it.
6. A deliberately clean PR must produce a green check; a deliberately
   vulnerable PR must produce a red check. Both must be demonstrated and
   verified before this phase is considered done.

## Forbidden behaviors
- Never make the gate advisory-only (warning without failing the build) —
  the entire narrative depends on it actually blocking merges.
- Never skip uploading the report artifact, even on failure — judges may
  want to inspect it.
- Never let a flaky negative-fixture test get silently skipped or disabled
  to make the pipeline green — if it's failing, the AST logic has a real
  false-positive bug and that's the priority fix, not the test.

## Verification checklist
- [ ] Clean PR → green check
- [ ] PR with seeded MD5/RSA-1024 → red check, build fails
- [ ] PR with only comment/variable-name mentions of "MD5" → green check
      (false-positive regression test)
- [ ] Report artifact downloadable from all three runs above
- [ ] Rehearsed live: someone opens a bad PR on stage and the red X appears
      within the demo's time budget — time this once beforehand, don't
      assume CI runtime is instant
