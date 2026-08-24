// Shared mock data — agreed shape for Day 1.
// Once the real API is ready (Day 4), swap the fetch calls in each
// component for real requests to the backend, keeping this same shape.

export const mockFindings = [
  {
    finding_id: 1,
    file: "auth/legacy_hash.py",
    line: 42,
    algorithm: "MD5",
    keyLength: null,
    assetType: "hash-function",
    severity: "Critical",
    riskTier: "Critical",
    suggestion: "Replace MD5 with SHA-256 or BLAKE2 for any security-relevant hashing.",
  },
  {
    finding_id: 2,
    file: "network/tls_config.py",
    line: 18,
    algorithm: "RSA",
    keyLength: 1024,
    assetType: "asymmetric-key",
    severity: "High",
    riskTier: "High",
    suggestion: "Upgrade RSA key size to 2048+ or migrate to Ed25519.",
  },
  {
    finding_id: 3,
    file: "utils/legacy_cipher.py",
    line: 7,
    algorithm: "DES",
    keyLength: 56,
    assetType: "symmetric-cipher",
    severity: "Critical",
    riskTier: "Critical",
    suggestion: "Replace DES with AES-256-GCM.",
  },
  {
    finding_id: 4,
    file: "api/session.py",
    line: 101,
    algorithm: "SHA-1",
    keyLength: null,
    assetType: "hash-function",
    severity: "Medium",
    riskTier: "Medium",
    suggestion: "Replace SHA-1 with SHA-256 for integrity checks.",
  },
];

// Sample single CBOM entry, shaped roughly like a CycloneDX
// cryptography-asset — Maitreyi will finalize the real schema Day 1.
export const mockCbomEntry = {
  bomFormat: "CycloneDX",
  specVersion: "1.6",
  components: [
    {
      type: "cryptographic-asset",
      name: "MD5",
      cryptoProperties: {
        assetType: "hash-function",
        algorithmProperties: {
          keyLength: null,
        },
      },
      evidence: {
        occurrences: [{ location: "auth/legacy_hash.py", line: 42 }],
      },
    },
  ],
};
