# Skill: Remediation Copy Generation

## Purpose
Turn a scanner finding + its risk score into a short, trustworthy sentence a
developer would actually believe — without ever becoming the source of truth
for *what* the fix is. The fix itself always comes from a fixed rule-based
lookup table; the LLM (if used) only rephrases it.

## Why this skill exists
This is the one place in the pipeline where an LLM touches user-facing text.
Every other component (scanner, risk score, CBOM) is fully deterministic —
this skill has to earn the right to use an LLM at all, and it does that by
keeping the LLM strictly downstream of a ground-truth answer, never upstream
of it.

## When to use this skill
After a finding has a canonical algorithm, a risk tier, and a risk reason
(see `cbom-quantum-risk`), and before it's returned by the
`/remediation` API route.

## Required process

### 1. Rule-based table is the source of truth
Maintain a plain lookup table (Python dict) mapping canonical algorithm →
recommended fix, aligned with the purpose-aware mapping in
`cbom-quantum-risk/SKILL.md`:

```python
REMEDIATION_TABLE = {
    "MD5":  {"fix": "SHA-256 or BLAKE2", "note": "hashing — assess security margin"},
    "SHA1": {"fix": "SHA-256", "note": "hashing — assess security margin"},
    "DES":  {"fix": "AES-256-GCM", "note": "symmetric — check key size & data lifetime"},
    "3DES": {"fix": "AES-256-GCM", "note": "symmetric — check key size & data lifetime"},
    "RSA_LT_2048_SIGNATURE": {"fix": "RSA-3072+/Ed25519 now; ML-DSA (Dilithium-class) for PQC track", "note": "signature purpose"},
    "RSA_LT_2048_KEYEXCHANGE": {"fix": "ML-KEM (Kyber-class)", "note": "key-establishment purpose"},
}
```

This table alone must be able to power the `/remediation` endpoint with the
LLM completely switched off. Build and test it that way first.

### 2. LLM only rephrases — never invents the fix
If an LLM call is used, the prompt must include the table's answer as a given
fact, and ask only for phrasing:

> "This file uses MD5 at line 42 for hashing. The recommended fix is SHA-256
> or BLAKE2. Explain the risk and the fix in 1–2 sentences, like a senior
> engineer's PR comment. Do not suggest any fix other than the one given."

Keep the prompt short — every extra sentence costs free-tier quota, and this
is a 6-day build with 5 people sharing rate limits.

### 3. Selective calling
Only call the LLM for the highest-severity (HIGH/CRITICAL) findings, not
every single one — this saves both time and quota, and keeps the demo fast.
Everything below that tier gets the plain table text directly, unmodified.

### 4. Fallback is mandatory, not optional
If the LLM API is down, rate-limited, or times out, the endpoint must return
the plain rule-based table text immediately — the demo must never show a
blank or errored remediation field. Test this by deliberately breaking the
API key mid-build and confirming the fallback fires.

### 5. Language discipline
Never phrase output as a legal conclusion. Use:
- ✓ "Cryptographic weakness detected; potential security/compliance
  relevance" — then reference DPDP/NIST guidance separately.
- ✗ "DPDP violation detected."

Never claim the fix is the only correct one — phrase it as a recommendation,
not a mandate: "recommended fix," not "required fix."

## Forbidden behaviors
- No LLM call that decides *what* the fix is — the table decides, the LLM
  only phrases.
- No remediation text generated for a finding that doesn't already have a
  canonical algorithm + risk tier from upstream.
- No unbounded LLM calls (one per finding regardless of severity) — this
  burns shared team quota fast.
- No blank/error state shown to the user if the LLM is unavailable.
- No legal-conclusion language ("violation," "breach," "non-compliant").

## Output schema
```json
{
  "finding_id": "f_1023",
  "suggestion": "This file uses MD5 for hashing at line 42, which no longer offers an adequate security margin. Recommended fix: SHA-256 or BLAKE2.",
  "source": "llm" ,
  "fallback_used": false,
  "severity": "HIGH"
}
```
(`source` is `"llm"` or `"table"` depending on whether the fallback fired —
keep this field, it's useful for debugging live during the demo.)

## Test requirement
- Unit test: table lookup returns the correct fix for every algorithm in
  `REMEDIATION_TABLE`.
- Integration test: with the LLM API key deliberately invalidated, the
  endpoint still returns a non-empty `suggestion` with `source: "table"`.
- Manual check: read the actual LLM-phrased output for at least one HIGH
  finding before demo day — confirm it never contradicts the table's fix.
