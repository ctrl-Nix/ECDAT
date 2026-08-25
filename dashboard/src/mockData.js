export const mockFindings = [
  { id: "1", scan_id: "scan-101", file: "src/auth/legacy_login.py", line: 42, algorithm: "MD5", keyLength: null, assetType: "hash", severity: "Critical", suggestion: "Replace MD5 with SHA-256 or BLAKE2." },
  { id: "2", scan_id: "scan-101", file: "src/utils/cert_gen.py", line: 15, algorithm: "RSA", keyLength: 1024, assetType: "public-key", severity: "High", suggestion: "Upgrade RSA-1024 to RSA-2048 or Ed25519." },
  { id: "3", scan_id: "scan-101", file: "src/api/handlers.js", line: 88, algorithm: "SHA-1", keyLength: null, assetType: "hash", severity: "Medium", suggestion: "SHA-1 is deprecated. Migrate to SHA-256." },
  { id: "4", scan_id: "scan-101", file: "lib/encryption.c", line: 112, algorithm: "AES", keyLength: 128, assetType: "symmetric", severity: "Low", suggestion: "Consider migrating to AES-256-GCM for post-quantum safety." }
];

export const mockCbom = {
  bomFormat: "CycloneDX", specVersion: "1.5", version: 1,
  components: mockFindings.map(f => ({
    type: "cryptographic-asset", name: `${f.algorithm} Asset`,
    properties: [ { name: "filePath", value: f.file }, { name: "algorithm", value: f.algorithm } ]
  }))
};