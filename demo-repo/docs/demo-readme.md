# ECDAT Demo Repository

This repository contains a collection of cryptographic assets across multiple
categories for testing the ECDAT scanning pipeline.

## Categories

- **Python Source**: `src/python/` - Weak crypto usage via hashlib, PyCryptodome, cryptography
- **JavaScript Source**: `src/javascript/` - Node.js crypto weak usage
- **Java Source**: `src/java/` - javax.crypto and java.security weak usage
- **Config/IaC**: `config/` - YAML, Terraform, NGINX, K8s with weak TLS/ciphers
- **Dependencies**: `deps/` - package.json, pyproject.toml with vulnerable packages
- **Containers**: `containers/` - Dockerfile with vulnerable packages
- **Binaries**: `binaries/` - ELF binaries with crypto symbols

## Risk Tiers

- **HIGH RISK**: MD5, SHA-1, DES, 3DES, RC4, TLSv1.0, TLSv1.1, RSA-1024, pycrypto
- **PROBABLE**: TLSv1.2, RSA-2048
- **LOW/OK**: AES, SHA-256, SHA-512, TLSv1.3, RSA-4096
