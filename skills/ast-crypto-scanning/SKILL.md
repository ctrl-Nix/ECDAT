# Skill: AST-Based Cryptographic Scanning

## Purpose
Detect cryptographic algorithm usage in Python source code structurally (via
the `ast` module), not via string/regex matching, so the scanner survives
formatting variation and does not fire on comments, strings, or variable names.

## When to use this skill
Any time the scanner needs to detect a new algorithm, library call, or
key-size pattern, or when extending detection coverage.

## Required inputs
- A Python source file (as text)
- The current weak-algorithm/weak-keysize rule table

## Required process
1. Parse the file with `ast.parse()`. If parsing fails, log a `parse_error`
   finding with the file path and exception message — do NOT skip the file
   silently.
2. Walk the AST with `ast.NodeVisitor` (not raw string search) to find:
   - `Import` / `ImportFrom` nodes referencing crypto libraries (`hashlib`,
     `Crypto`, `cryptography`, etc.)
   - `Call` nodes invoking flagged functions (e.g. `hashlib.md5`, `DES.new`,
     `RSA.generate` with key size < 2048)
3. For each match, record: file path, line number, exact matched call/import
   (verbatim), library, algorithm, and — if statically determinable — key size
   or parameters.
4. Never infer risk from a comment, string literal, or variable name alone —
   only from actual `Call`/`Import` AST nodes. A comment containing "MD5" or a
   variable named `legacy_hash_unused` must NOT produce a finding.
5. Output findings as structured objects (not free text), ready for the
   CBOM/risk-scoring stage.

## Forbidden behaviors
- No regex-based matching, ever — this is a hard constitutional rule, not a
  preference.
- No flagging based on filenames, comments, or identifier names.
- No silent skip of unparseable files.
- No deduplication that discards the original evidence — always retain
  file + line + exact match.
- No claiming 100% detection anywhere in code, comments, or docs.

## Output schema
```json
{
  "file": "app/auth.py",
  "line": 42,
  "matched_call": "hashlib.md5(password.encode())",
  "library": "hashlib",
  "algorithm": "MD5",
  "key_size": null,
  "confidence": "high"
}
```

## Test requirement
Every new detection rule needs TWO fixtures:
1. **Positive fixture** — a file containing the exact vulnerability. The
   scanner must catch it.
2. **Negative fixture** — a file where the algorithm name appears only in a
   comment, string literal, or identifier name (e.g. `# uses MD5` or
   `legacy_hash_unused = True`), with no real call. The scanner must produce
   **zero** findings on this file.

Before Phase/Day sign-off for the scanner, run both fixture sets together and
confirm: all positives caught, zero false positives on negatives. This pair is
also the artifact for the "false positives minimized through AST
context-awareness" demo line — don't lose it, it's your strongest live-Q&A
answer.

## Benchmark requirement (do this once the rule table is stable)
Run the scanner against three repositories and record results:
- **Repo A** — seeded weak crypto (5–10 known-bad patterns)
- **Repo B** — mostly modern/secure crypto (should stay mostly clean)
- **Repo C** — mixed real-world code (the realistic case)

Report detection accuracy / false-positive rate across the three. This is
stronger evidence than a single demo file and defuses "did you just hard-code
the result?" on stage.
