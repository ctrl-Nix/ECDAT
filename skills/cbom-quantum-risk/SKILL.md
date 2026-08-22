# Skill: CBOM Generation & Quantum-Risk Scoring

## Purpose
Convert raw scanner findings into a standardized CycloneDX-shaped CBOM, and
assign each finding an **explainable, rule-based** quantum-risk score with a
**purpose-aware** PQC/hybrid remediation direction. No black-box AI number is
acceptable here — every score must be traceable to named factors.

## When to use this skill
After the AST scanner (see `ast-crypto-scanning`) has produced structured
findings for a scan run.

## Required process

### 1. Normalize
Normalize each finding to canonical algorithm names (e.g. `md5`, `MD5`,
`hashlib.md5` → `MD5`) while preserving the original raw string as evidence —
never overwrite it.

### 2. Score — explainable heuristic risk model
Map each canonical algorithm/key-size to a quantum-risk tier using a
Mosca's-theorem-style model built from three named, documented factors:

- `migration_time` — how long it would realistically take to replace this
  usage (low/medium/high effort)
- `threat_horizon` — how soon this algorithm class is expected to be broken
  by quantum attacks (symmetric algorithms like AES-256 are low risk;
  RSA/ECC key-exchange and signatures are high risk)
- `data_shelf_life` — how long data protected by this instance needs to stay
  confidential

**Rule:** Risk = HIGH if `migration_time + data_shelf_life > threat_horizon`,
else scale down through MEDIUM/LOW. Document the exact weights/thresholds you
use in this file once decided — do not leave them implicit in code only.

Every MEDIUM+ finding must carry a one-sentence `risk_reason` string built
from the three factors above, e.g.: *"RSA-1024 used for signing; short
migration time but long data shelf-life exceeds the estimated threat
horizon — HIGH."* If you can't write that sentence, the score isn't ready.

**Never** replace this with an LLM-generated risk number. An LLM may
*phrase* the `risk_reason` sentence for readability (see
`remediation-copy`), but the tier itself must come from the rule above.

### 3. Classify — type, lifetime, and business criticality (PS requirement)
The PS explicitly requires classification along three dimensions: **type**,
**lifetime**, and **business criticality**. Type and lifetime come from steps
1–2 above. Criticality is a separate field, populated as follows:

```python
def get_criticality(file_path: str) -> str:
    """
    Simple, explainable keyword match on file path — not a model, not a
    guess. Judges can see exactly why a finding got tagged CRITICAL.
    """
    path = file_path.lower()
    if any(k in path for k in ["auth", "login", "payment", "billing", "session"]):
        return "CRITICAL"
    elif any(k in path for k in ["api", "service", "core", "db", "database"]):
        return "HIGH"
    else:
        return "MEDIUM"
```

This populates the `criticality` column reserved in `ARCHITECTURE.md`. A
finding is only "classification-complete" once it has type + lifetime +
criticality all set — this is a `.clinerules` rule (#17), not optional polish.

### 4. Recommend — purpose-aware, not blanket substitution
Map by cryptographic **purpose** first, then recommend the matching PQC
direction. Do not do a blind find-and-replace on algorithm name.

| Current use            | Migration direction                                   |
|-------------------------|--------------------------------------------------------|
| Key establishment       | PQ / hybrid KEM (ML-KEM / Kyber-class)                 |
| Digital signature       | PQ signature (ML-DSA / Dilithium-class)                |
| Symmetric encryption    | Assess key size & data lifetime — often not a PQC swap |
| Hashing                 | Assess security margin, not a like-for-like replacement|

Concrete lookup examples:
- MD5 (hashing) → SHA-256 or BLAKE2, plus a security-margin note
- SHA-1 (hashing) → SHA-256
- DES/3DES (symmetric) → AES-256-GCM
- RSA < 2048 used for **signatures** → RSA-3072+/Ed25519 now, ML-DSA/Dilithium
  as the PQC-track answer
- RSA < 2048 used for **key exchange** → ML-KEM/Kyber-class as the PQC-track
  answer

### 5. Emit CBOM
Emit output as CycloneDX JSON with the cryptography-asset extension fields
populated (algorithm, key length, asset type, evidence reference, risk tier,
risk reason, criticality, recommended migration direction).

## Forbidden behaviors
- Never assign a risk score without recording the rationale — a bare severity
  label with no reasoning is not acceptable.
- Never invent a CycloneDX field structure — follow the actual spec fields,
  even if minimal.
- Never recommend a PQC swap without checking cryptographic purpose first
  (no blanket "RSA → ML-KEM" regardless of use).
- Do not implement or hand-roll actual PQC algorithms. Recommend standards
  only; never write your own crypto primitive.
- Never phrase a finding as a legal conclusion ("DPDP violation"). Use
  "potential security/compliance relevance" and reference the guidance.

## Output requirement
A single scan run must produce one valid CBOM JSON file that a CycloneDX
validator (or manual schema check) would accept, with every finding
traceable back to its scanner evidence and its risk-scoring rationale.
