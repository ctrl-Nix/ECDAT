# ECDAT Live Demo Repository

This deliberately small repository contains representative **non-production**
crypto API calls for a sub-minute ECDAT demonstration. It contains no secrets,
network calls, build scripts, or deployable application logic.

Run it locally through the ECDAT container image:

```bash
docker run --rm -v "$PWD":/target:ro --entrypoint python ecdat-secure-pipeline:local \
  -m scanner.cli /target --summary-only --source-context DEMO_ONLY --fail-on HIGH
```

Verified on the supplied Python 3.11 image in approximately **one second**:
ECDAT reports **9** high-confidence inventory records—**4 Critical**, **3
High**, and **2 Low**—then exits with code `2` because the demonstration
contains Critical and High policy violations. The examples deliberately cover
MD5, SHA-1, 3DES, RSA, and SHA-256 across Python, Java, JavaScript, and
TypeScript. The explicit `DEMO_ONLY` label is part of the command so none of
these non-production examples can be mistaken for deployed exposure.
