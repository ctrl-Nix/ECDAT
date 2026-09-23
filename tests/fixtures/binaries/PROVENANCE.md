# Binary Test Fixtures Provenance

This directory contains test fixture binaries for `scanner/binary_engine.py` unit and integration tests.

## Fixtures

### `libcrypto_positive.elf`
- **Format:** 64-bit ELF executable (x86-64, little-endian)
- **Constructed with:** Python `struct` script generating valid ELF64 header, `.text`, `.rodata`, `.dynsym`, `.dynstr`, and section header table.
- **Contents:**
  - Dynamic symbols: `MD5_Init`, `AES_encrypt`, `EVP_sha256`
  - Dynamic needed library: `libcrypto.so`
  - `.rodata` section: Contains AES S-Box bytes (`637c777bf26b6fc53001672bfed7ab76`) and MD5 initial state constants (`0123456789abcdeffedcba9876543210`).
- **Expected findings:**
  - Tier 1 (Symbol table): `MD5_Init` (MD5), `AES_encrypt` (AES), `EVP_sha256` (SHA-256)
  - Tier 2 (Constant scan): AES S-Box in `.rodata`, MD5 IV in `.rodata`

### `clean_decoy.elf`
- **Format:** 64-bit ELF executable (x86-64, little-endian)
- **Constructed with:** Python `struct` script.
- **Contents:** Standard C library imports (`printf`, `malloc`, `free`, `exit`) and non-cryptographic text data.
- **Expected findings:** 0 findings.

### `crypto_sample.exe`
- **Format:** 32-bit PE executable (x86, little-endian)
- **Constructed with:** Python `struct` script generating valid DOS header, PE COFF header, optional header, `.text`, and `.rdata` with import directory table.
- **Contents:**
  - Imported DLL: `libcrypto.dll`
  - Imported functions: `MD5_Init`, `DES_set_key`
  - `.rdata` section: Contains AES S-Box bytes (`637c777bf26b6fc53001672bfed7ab76`).
- **Expected findings:**
  - Tier 1: `MD5_Init` (MD5), `DES_set_key` (DES), `libcrypto.dll` (UNKNOWN)
  - Tier 2: AES S-Box in `.rdata`

### `clean_sample.exe`
- **Format:** 32-bit PE executable (x86, little-endian)
- **Constructed with:** Python `struct` script.
- **Contents:** Standard Win32 imports (`ExitProcess`, `GetStdHandle`) from `kernel32.dll`.
- **Expected findings:** 0 findings.

### `adversarial_decoy.bin`
- **Format:** ASCII plain text (non-binary)
- **Contents:** Mentions crypto strings in comments without binary headers.
- **Expected findings:** 0 findings (unsupported binary format).
