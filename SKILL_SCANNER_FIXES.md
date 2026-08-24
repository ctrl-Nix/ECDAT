# SKILL: Scanner Engine Fixes
## Scope: Library Field Reconciliation + key_size Extraction for Java/JS

---

## Context

The ECDAT scanner has two engines:
1. **Python Engine** (`scanner/python_engine.py`) — uses stdlib `ast`
2. **Multi-Lang Engine** (`scanner/multilang_engine.py`) — uses tree-sitter for Java/JS

Both emit the same `Finding` dataclass (`scanner/finding.py`), but two inconsistencies exist:

### Inconsistency 1: `library` field semantics
- **Python engine:** `library` = canonical library name (`"hashlib"`, `"PyCryptodome"`, `"cryptography"`, `"ssl"`)
- **Multi-lang engine:** `library` = literal object identifier from code (`"MessageDigest"`, `"crypto"`)

These are different kinds of values. The CBOM generator and dashboard expect canonical library names.

### Inconsistency 2: `key_size` extraction
- **Python engine:** Extracts RSA key size from `rsa.generate_private_key(key_size=1024)` or positional arg
- **Multi-lang engine:** Does NOT extract key sizes for Java (`KeyPairGenerator.getInstance("RSA", 2048)`) or JS

---

## Task 1: Reconcile `library` Field Semantics

### Decision
**Both engines must emit canonical library names.**

### Implementation Plan

#### For Python Engine (`scanner/python_engine.py`)
No changes needed. Already emits canonical names.

Verify the `CALL_RULES` dict uses these canonical names:
- `"hashlib"` for hashlib calls
- `"PyCryptodome"` for DES.new / ARC4.new / AES.new
- `"cryptography"` for RSA.generate / rsa.generate_private_key
- `"ssl"` for ssl.SSLContext / ssl.wrap_socket

#### For Multi-Lang Engine (`scanner/multilang_engine.py`)
Add a `canonical_library` field to each rule in `rules/java.yaml` and `rules/javascript.yaml`.

**Update `rules/java.yaml`:**
```yaml
language: java
rules:
  - id: java-md5
    match_object: MessageDigest
    match_method: getInstance
    match_arg_contains: MD5
    expected_import: java.security.MessageDigest
    canonical_library: "java.security.MessageDigest"
    algorithm: MD5
    primitive: hash
    weak_by_default: true
  # ... add canonical_library to ALL rules
```

**Update `rules/javascript.yaml`:**
```yaml
language: javascript
rules:
  - id: js-md5
    match_object: crypto
    match_method: createHash
    match_arg_contains: md5
    expected_module: crypto
    canonical_library: "crypto"
    algorithm: MD5
    primitive: hash
    weak_by_default: true
  # ... add canonical_library to ALL rules
```

**Update `multilang_engine.py`:**
In the rule matching logic, when a rule matches:
```python
# OLD:
library = object_name  # "MessageDigest" or "crypto"

# NEW:
library = rule.get("canonical_library", object_name)
```

This preserves backward compatibility while allowing rules to specify the correct canonical name.

### Verification
After changes, run:
```bash
python -m scanner.cli tests/fixtures/ --json-out findings.json
```

Verify:
- Java findings have `library` = `"java.security.MessageDigest"`, `"javax.crypto.Cipher"`, etc.
- JavaScript findings have `library` = `"crypto"`
- Python findings remain unchanged

---

## Task 2: Add key_size Extraction for Java and JavaScript

### Decision
Extract key size from arguments when statically determinable, same as Python engine.

### Java Implementation

**Target pattern:** `KeyPairGenerator.getInstance("RSA", 2048)` or `.initialize(1024)`

In `multilang_engine.py`, add:

```python
def extract_key_size_java(args_node, source_code, rule):
    if rule.get("primitive") != "asymmetric-keygen":
        return None

    args_text = source_code[args_node.start_byte:args_node.end_byte]
    import re
    numbers = re.findall(r'\b(\d{3,5})\b', args_text)
    for num_str in numbers:
        n = int(num_str)
        if 512 <= n <= 16384:
            return n
    return None
```

**Update the Java rule:**
```yaml
  - id: java-rsa-keygen
    match_object: KeyPairGenerator
    match_method: getInstance
    match_arg_contains: RSA
    expected_import: java.security.KeyPairGenerator
    canonical_library: "java.security.KeyPairGenerator"
    algorithm: RSA
    primitive: asymmetric-keygen
    weak_by_default: false
    extract_key_size: true
```

### JavaScript Implementation

**Target pattern:** `crypto.generateKeyPairSync('rsa', { modulusLength: 1024 })`

```python
def extract_key_size_js(args_node, source_code, rule):
    if rule.get("primitive") != "asymmetric-keygen":
        return None

    args_text = source_code[args_node.start_byte:args_node.end_byte]
    import re
    mod_match = re.search(r'modulusLength\s*[:=]\s*(\d{3,5})', args_text)
    if mod_match:
        n = int(mod_match.group(1))
        if 512 <= n <= 16384:
            return n

    numbers = re.findall(r'\b(\d{3,5})\b', args_text)
    for num_str in numbers:
        n = int(num_str)
        if 512 <= n <= 16384:
            return n
    return None
```

**Add JS RSA keygen rule:**
```yaml
  - id: js-rsa-keygen
    match_object: crypto
    match_method: generateKeyPairSync
    match_arg_contains: rsa
    expected_module: crypto
    canonical_library: "crypto"
    algorithm: RSA
    primitive: asymmetric-keygen
    weak_by_default: false
    extract_key_size: true
```

### Wiring in multilang_engine.py

```python
key_size = None
if rule.get("extract_key_size"):
    if language == "java":
        key_size = extract_key_size_java(args_node, source_code, rule)
    elif language == "javascript":
        key_size = extract_key_size_js(args_node, source_code, rule)

finding = Finding(
    file=file_path,
    line=line_number,
    matched_call=matched_call_text,
    library=rule.get("canonical_library", object_name),
    algorithm=rule["algorithm"],
    primitive=rule["primitive"],
    language=language,
    weak_by_default=rule["weak_by_default"],
    confidence=confidence,
    key_size=key_size,
    detection_method="static_analysis"
)
```

### Test Fixtures to Add

**`tests/fixtures/java/RsaKeyService.java`:**
```java
import java.security.KeyPairGenerator;

public class RsaKeyService {
    public void generateWeakKey() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(1024);
    }

    public void generateStrongKey() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(4096);
    }
}
```

**`tests/fixtures/javascript/cryptoService.js`:**
```javascript
const crypto = require('crypto');

function generateWeakKey() {
    return crypto.generateKeyPairSync('rsa', {
        modulusLength: 1024,
    });
}

function generateStrongKey() {
    return crypto.generateKeyPairSync('rsa', {
        modulusLength: 4096,
    });
}
```

### Verification Steps
1. Add test fixtures above
2. Run scanner against fixtures
3. Verify Java findings include `key_size: 1024` and `key_size: 4096`
4. Verify JS findings include `key_size: 1024` and `key_size: 4096`
5. Verify existing tests still pass (no regressions)
6. Verify `library` field uses canonical names for all Java/JS findings

---

## Deliverables

1. Updated `rules/java.yaml` with `canonical_library` and `extract_key_size` fields
2. Updated `rules/javascript.yaml` with `canonical_library`, `extract_key_size`, and new `js-rsa-keygen` rule
3. Updated `scanner/multilang_engine.py` with extraction functions and modified finding creation
4. New test fixtures: `java/RsaKeyService.java`, `javascript/cryptoService.js`
5. Updated test expectations in README if counts change
