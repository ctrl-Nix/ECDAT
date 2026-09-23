# ECDAT Container-Scanning Scope and Evidence Contract

Container image scanning discovers cryptographic assets (X.509 certificates, private keys, and installed cryptographic library packages) within local container images and layers.

## Supported inputs
- **OCI Image Tarballs (`docker save` format):** Standard image archives containing `manifest.json`, layer tarballs, and image configuration JSON.
- **OCI Image-Layout Directories:** Filesystem directories formatted per the OCI Image Layout Specification containing `index.json`, `oci-layout`, and layer blob directories.
- **Layer Packaging Metadata:** Debian (`var/lib/dpkg/status`), Alpine (`lib/apk/db/installed`), RPM metadata, and container-shipped language manifests (`requirements.txt`, `package-lock.json`, `META-INF/MANIFEST.MF`).
- **Cryptographic File Objects:** PEM and DER formatted X.509 certificates and PKCS#8/PKCS#1 private keys anywhere within the extracted container layers.

## Deliberate non-claims
- **No Docker Socket / Daemon Access:** Scanning is purely static and offline; it never mounts `/var/run/docker.sock` or calls the Docker/Podman daemon.
- **No Network Egress / Registry Pulls:** Does not pull from remote registries (Docker Hub, ECR, GCR, etc.) or initiate any outbound network connections.
- **No Proof of Runtime Execution:** Discovering a library package or certificate in a container layer confirms its presence on the image filesystem, not whether it is loaded into memory or executed at runtime.
- **No Binary Linkage Inspection:** Does not disassemble or resolve dynamic ELF symbols inside container binaries (covered separately by the Binary Scanning engine).

## Confidence semantics
- **Explicit Cryptographic Evidence:** Certificate parsing extracts verifiable cryptographic parameters (algorithm, key length, signature algorithm) directly from parsed ASN.1 structures with `confidence: "high"` and `confidence_band: "VERIFIED"`.
- **Package Inventory Evidence:** Package presence extracted from package manager databases is emitted with `confidence: "high"` and `detection_method: "container_package_inventory"`. What is verified is the static installation of the library on the container filesystem.

## Package-inventory evidence strength
Package inventory matches installed package records against `scanner/rules/container.yaml`. It captures the ecosystem, package name, and exact installed version, and attributes the finding to the specific layer digest that introduced or updated the package record.

## Certificate-parsing evidence strength
Certificate parsing utilizes `cryptography.x509` (not regular expressions) to decode X.509 certificates and private keys. Findings record exact key sizes (e.g., RSA-1024, RSA-2048, RSA-4096) and algorithms, mapping directly into the quantum risk engine.

## Safe rollout
- CLI-driven scanning (`--scan-type container --image-tar <PATH>`) operates completely offline.
- Total extraction size is guarded by `SCAN_MAX_ARTIFACT_BYTES` to prevent decompression bombs.
- Path traversal protections reject any archive entries containing absolute paths or `..` path segments.
