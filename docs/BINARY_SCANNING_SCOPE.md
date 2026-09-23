# Binary Scanning (Heuristic) Scope

Binary cryptographic scanning (`--scan-type binary`) provides heuristic detection of cryptographic usage in compiled native executable and library binaries.

## Supported Binary Formats
- **ELF (Linux / Unix):** `.so` shared libraries, ELF executables, relocatable object files
- **PE (Windows):** `.dll` dynamic link libraries, `.exe` executables, `.sys` drivers
- **Mach-O (macOS):** `.dylib` shared libraries, Mach-O executables, universal/fat binaries

## Detection Tiers and Confidence

### Tier 1: Linkage & Symbol Table Discovery
- **Detection Method:** `binary_symbol_table`
- **Mechanism:** Inspects dynamic symbol tables (`.dynsym`), imported symbols, exported symbols, and needed shared library dependencies (`DT_NEEDED` / import tables).
- **Confidence:** `confidence: "high"`, `confidence_band: "VERIFIED"` (score 0.85–0.90)
- **Evidence Reference:** Emits `artifact_ref` in format `"<symbol_table>:<symbol_name>"` (e.g., `.dynsym:MD5_Init`).

### Tier 2: Read-Only Data Section Constant Matching
- **Detection Method:** `binary_constant_scan`
- **Mechanism:** Fixed cryptographic signature scanning across read-only data sections (`.rodata`, `.rdata`, `__TEXT.__const`) for known constants (e.g., AES S-box, MD5/SHA initial hash constants).
- **Confidence:** `confidence: "unverified"`, `confidence_band: "UNVERIFIED"` (score 0.35)
- **Evidence Reference:** Emits `artifact_ref` in format `"<section>+0x<offset>"` (e.g., `.rodata+0x1040`).

## Line Numbers
Binary artifacts do not contain line numbers. The `line` field is always `0` (rendered as `—` in the dashboard).

## Confidence Gate & Persistence Policy (C-02)
- Tier-1 findings (`confidence: "high"`) are emitted to CLI/JSON and persisted to the database.
- Tier-2 findings carry legacy `confidence: "unverified"`. Under the pre-CONF database gate in `scan_runner.py`, tier-2 findings are printed in CLI output but are not stored in the database until CONF's configurable confidence gate (`SCAN_MIN_CONFIDENCE_BAND`) is active.

## Limitations & What This Feature Is Not
- **No De-obfuscation / Unpacking:** Does not defeat runtime packers (e.g., UPX, custom packers) or encrypted binary sections.
- **No Disassembly / Control-Flow Analysis:** Does not perform full instruction decoding, CFG reconstruction, or reachability proof.
- **No Proof of Runtime Execution:** Discovery indicates compilation/linkage of cryptographic primitives; it does not prove execution at runtime.
- **Static & Offline:** Scans static files on disk without executing target binaries or invoking dynamic container runtimes.
