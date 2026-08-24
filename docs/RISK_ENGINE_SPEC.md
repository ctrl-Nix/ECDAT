# ECDAT Risk Engine Specification
## Quantum-Aware Cryptographic Risk Scoring

---

## 1. Core Philosophy

**Not every weak finding is a quantum-risk finding.**

The risk engine operates on **two independent axes**:

| Axis | Question | Examples |
|---|---|---|
| **Classical Security** | Is this broken by today's computers? | MD5, SHA-1, DES, RC4, RSA-1024 |
| **Quantum Vulnerability** | Will quantum computers break this? | RSA, ECC, DH, DSA (all sizes) |

A finding can be:
- Classically broken AND not quantum-relevant (MD5)
- Not classically broken BUT quantum-vulnerable (RSA-4096)
- Both (RSA-1024)
- Neither (AES-256-GCM)

**Conflating these axes is the #1 mistake judges will test for.**

---

## 2. Risk Tier Rules

The risk engine is **rule-based**, not ML-based. Rules are deterministic and auditable.

### Algorithm Risk Table

```python
RISK_RULES = {
    # Hashes
    "MD5": {
        "tier": "Critical",
        "classical_broken": True,
        "classical_break_detail": "practically broken (collision attacks known, < 2^18 cost)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "SHA-256",
        "recommendation_type": "classical",
        "migration_effort_days": 1,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 18
    },
    "SHA-1": {
        "tier": "Critical",
        "classical_broken": True,
        "classical_break_detail": "practically broken (SHAttered collision, ~$45k cloud cost)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "SHA-256",
        "recommendation_type": "classical",
        "migration_effort_days": 1,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 63
    },
    "SHA-256": {
        "tier": "Low",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm reduces effective security to 128 bits — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "classical_security_level": 256
    },

    # Symmetric Encryption
    "DES": {
        "tier": "Critical",
        "classical_broken": True,
        "classical_break_detail": "practically broken (brute-force feasible since 1999)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "AES-256-GCM",
        "recommendation_type": "classical",
        "migration_effort_days": 3,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 56
    },
    "RC4": {
        "tier": "Critical",
        "classical_broken": True,
        "classical_break_detail": "practically broken (statistical biases, RFC 7465 prohibits use)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "AES-256-GCM",
        "recommendation_type": "classical",
        "migration_effort_days": 3,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 0
    },
    "AES-256": {
        "tier": "Low",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm reduces to 128-bit equivalent — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "classical_security_level": 256
    },

    # Asymmetric
    "RSA": {
        "tier": "High",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks all RSA key sizes in polynomial time",
        "recommended_replacement": "ML-KEM-768 + ML-DSA-65 (hybrid with RSA-3072+)",
        "recommendation_type": "hybrid",
        "migration_effort_days": 30,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "classical_security_level": "variable"
    },
    "ECC": {
        "tier": "High",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks all ECC curves in polynomial time",
        "recommended_replacement": "ML-KEM-768 + ML-DSA-65",
        "recommendation_type": "post-quantum",
        "migration_effort_days": 30,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "classical_security_level": "variable"
    },
    "DSA": {
        "tier": "High",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks DSA in polynomial time",
        "recommended_replacement": "ML-DSA-65",
        "recommendation_type": "post-quantum",
        "migration_effort_days": 21,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "classical_security_level": "variable"
    },

    # Protocols
    "TLS-1.0": {
        "tier": "Critical",
        "classical_broken": True,
        "classical_break_detail": "practically broken (POODLE, BEAST attacks)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "TLS-1.3",
        "recommendation_type": "classical",
        "migration_effort_days": 7,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 0
    },
    "TLS-1.1": {
        "tier": "High",
        "classical_broken": True,
        "classical_break_detail": "deprecated (no modern cipher suites)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "TLS-1.3",
        "recommendation_type": "classical",
        "migration_effort_days": 7,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "classical_security_level": 0
    },
    "TLS-1.2": {
        "tier": "Medium",
        "classical_broken": False,
        "classical_break_detail": "acceptable if configured securely",
        "quantum_vulnerable": False,
        "quantum_break_detail": "Not quantum-broken, but lacks PQC key exchange",
        "recommended_replacement": "TLS-1.3 with hybrid PQC (draft)",
        "recommendation_type": "hybrid",
        "migration_effort_days": 14,
        "data_shelf_life_years": 5,
        "nist_quantum_security_level": 0,
        "classical_security_level": 128
    },
    "TLS-1.3": {
        "tier": "Low",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Not yet quantum-broken; PQC extensions in draft",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "classical_security_level": 128
    }
}
```

### Key-Size Override Rules

For RSA and ECC, the base algorithm rule is modified by key size:

```python
def apply_key_size_override(algorithm, key_size):
    if algorithm == "RSA":
        if key_size and key_size < 2048:
            return {
                "tier": "Critical",
                "classical_broken": True,
                "classical_break_detail": f"RSA-{key_size} is factorable by classical means",
                "override_reason": "insufficient_key_size"
            }
        elif key_size and key_size == 2048:
            return {"tier": "Medium"}  # Still quantum-vulnerable but classically okay
    return {}  # No override
```

---

## 3. Mosca's Theorem Adaptation

For quantum-vulnerable findings (RSA, ECC, DH, DSA), we apply a simplified Mosca-style assessment:

```
If (data_shelf_life + migration_time) > quantum_threat_horizon:
    -> Urgent: Data will still be sensitive when quantum computers arrive

Where:
  data_shelf_life = how long must this data remain confidential (enterprise-defined)
  migration_time  = estimated effort from RISK_RULES (days)
  quantum_threat_horizon = 10-15 years (NIST estimate for cryptographically-relevant quantum computer)
```

**In practice for hackathon:** We pre-populate `data_shelf_life_years` in the rules table based on algorithm typical usage. Enterprises can override per-repo in future versions.

---

## 4. Database Schema (risk_assessments)

```sql
CREATE TABLE risk_assessments (
    id                            SERIAL PRIMARY KEY,
    finding_id                    INTEGER NOT NULL UNIQUE REFERENCES findings(id) ON DELETE CASCADE,
    risk_tier                     TEXT NOT NULL CHECK (risk_tier IN ('Low','Medium','High','Critical')),
    migration_effort_days         INTEGER,
    quantum_threat_horizon_years  INTEGER,
    data_shelf_life_years         INTEGER,
    classical_break_status        TEXT,
    quantum_break_status          TEXT,
    recommended_replacement       TEXT,
    recommendation_type           TEXT CHECK (recommendation_type IN ('classical','hybrid','post-quantum')),
    scored_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 5. Execution Flow

```
Scan completes -> findings saved to DB
                      |
                      v
              [Background Task]
              For each finding:
                1. Lookup algorithm in RISK_RULES
                2. Apply key_size override if applicable
                3. Compute Mosca urgency flag
                4. Insert row into risk_assessments
                      |
                      v
              Dashboard shows enriched findings
```

---

## 6. Pitch-Ready Talking Points

- "MD5 and SHA-1 are already broken by classical attacks — this isn't about quantum computers. RSA and ECC are the ones that quantum computers will actually break via Shor's algorithm."
- "We separate evidence from interpretation: the scanner says 'we found MD5 on line 14'. The risk engine says 'MD5 is Critical-tier because collision attacks cost under $100 in cloud compute.'"
- "Our CBOM uses the real CycloneDX 1.6 cryptographic-asset specification — the same standard IBM, OWASP, and the US government are standardizing on."
