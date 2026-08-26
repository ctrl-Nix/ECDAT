// ── Rich mock data for ECDAT enterprise dashboard ──────────────────────────

export const mockFindings = [
  { id: 1, file: 'src/auth/legacy_login.py', algorithm: 'MD5', line: 42, severity: 'CRITICAL', risk_tier: 'CRITICAL', confidence: 'high', quantum_vulnerable: false, classical_broken: true, replacement: 'SHA-256 or BLAKE2', date: '2026-08-24', scan_id: 101, summary: 'Legacy MD5 hash used for password verification — classically broken (collision attacks <2^18 cost).' },
  { id: 2, file: 'src/utils/cert_gen.py', algorithm: 'RSA-1024', line: 15, severity: 'CRITICAL', risk_tier: 'CRITICAL', confidence: 'high', quantum_vulnerable: true, classical_broken: true, replacement: 'RSA-3072+ or ML-KEM-768', date: '2026-08-23', scan_id: 101, summary: 'RSA-1024 is classically factorable by GNFS and broken by Shor\'s algorithm.' },
  { id: 3, file: 'src/api/handlers.js', algorithm: 'SHA-1', line: 88, severity: 'HIGH', risk_tier: 'HIGH', confidence: 'medium', quantum_vulnerable: false, classical_broken: true, replacement: 'SHA-256', date: '2026-08-22', scan_id: 101, summary: 'SHA-1 deprecated (SHAttered). Used in token signing — immediate replacement needed.' },
  { id: 4, file: 'lib/encryption.c', algorithm: 'AES-128', line: 112, severity: 'MEDIUM', risk_tier: 'MEDIUM', confidence: 'high', quantum_vulnerable: false, classical_broken: false, replacement: 'AES-256-GCM', date: '2026-08-21', scan_id: 102, summary: 'AES-128 with Grover\'s algorithm reduces to 64-bit effective security. Migrate to AES-256-GCM.' },
  { id: 5, file: 'services/payment/rsa_sign.java', algorithm: 'RSA-2048', line: 33, severity: 'HIGH', risk_tier: 'HIGH', confidence: 'high', quantum_vulnerable: true, classical_broken: false, replacement: 'ML-DSA-65 (FIPS 204)', date: '2026-08-20', scan_id: 102, summary: 'RSA-2048 is quantum-vulnerable via Shor\'s algorithm. Mosca urgency: migrate before 2030.' },
  { id: 6, file: 'infra/tls_config.go', algorithm: 'TLS-1.0', line: 7, severity: 'CRITICAL', risk_tier: 'CRITICAL', confidence: 'high', quantum_vulnerable: false, classical_broken: true, replacement: 'TLS-1.3', date: '2026-08-19', scan_id: 103, summary: 'TLS 1.0 is classically broken (POODLE, BEAST). Deprecated by RFC 8996.' },
  { id: 7, file: 'core/crypto/ecdsa.rs', algorithm: 'ECC', line: 201, severity: 'HIGH', risk_tier: 'HIGH', confidence: 'medium', quantum_vulnerable: true, classical_broken: false, replacement: 'ML-DSA-65 (FIPS 204)', date: '2026-08-18', scan_id: 103, summary: 'ECDSA is broken by Shor\'s algorithm in polynomial time regardless of curve.' },
  { id: 8, file: 'src/legacy/des_cipher.py', algorithm: 'DES', line: 56, severity: 'CRITICAL', risk_tier: 'CRITICAL', confidence: 'high', quantum_vulnerable: false, classical_broken: true, replacement: 'AES-256-GCM', date: '2026-08-17', scan_id: 101, summary: 'DES 56-bit key is brute-forceable since 1999 (EFF DES Cracker). Immediate replacement required.' },
  { id: 9, file: 'src/session/hmac_verify.py', algorithm: 'HMAC-SHA256', line: 19, severity: 'LOW', risk_tier: 'LOW', confidence: 'high', quantum_vulnerable: false, classical_broken: false, replacement: null, date: '2026-08-16', scan_id: 102, summary: 'HMAC-SHA256 is secure. No action required.' },
  { id: 10, file: 'config/ssl/openssl.conf', algorithm: 'TLS-1.3', line: 3, severity: 'LOW', risk_tier: 'LOW', confidence: 'high', quantum_vulnerable: false, classical_broken: false, replacement: null, date: '2026-08-15', scan_id: 102, summary: 'TLS 1.3 is the recommended version. Continue using.' },
];

export const mockScans = [
  { id: 101, repository: 'github.com/enterprise/core-banking', branch: 'main', status: 'completed', findings: 5, critical: 3, date: '2026-08-24', duration: '2m 14s', languages: ['Python', 'Java'] },
  { id: 102, repository: 'github.com/enterprise/payments', branch: 'release-2.4', status: 'completed', findings: 4, critical: 1, date: '2026-08-23', duration: '1m 47s', languages: ['Java', 'Rust'] },
  { id: 103, repository: 'github.com/enterprise/identity', branch: 'develop', status: 'failed', findings: 2, critical: 1, date: '2026-08-22', duration: '0m 33s', languages: ['Go'] },
  { id: 104, repository: 'github.com/enterprise/api-gateway', branch: 'main', status: 'running', findings: 0, critical: 0, date: '2026-08-26', duration: '—', languages: ['TypeScript'] },
];

export const mockCbom = {
  bomFormat: 'CycloneDX',
  specVersion: '1.6',
  version: 1,
  serialNumber: 'urn:uuid:ecdat-cbom-2026-08-24',
  metadata: {
    timestamp: '2026-08-24T10:30:00Z',
    tools: [{ vendor: 'Port53', name: 'ECDAT', version: '1.0.0' }],
  },
  components: mockFindings.map((f) => ({
    type: 'cryptographic-asset',
    name: `${f.algorithm} Asset`,
    version: '1.0',
    cryptoProperties: {
      assetType: 'algorithm',
      algorithmProperties: { primitive: f.algorithm },
    },
    properties: [
      { name: 'ecdat:filePath', value: f.file },
      { name: 'ecdat:line', value: String(f.line) },
      { name: 'ecdat:riskTier', value: f.risk_tier },
      { name: 'ecdat:quantumVulnerable', value: String(f.quantum_vulnerable) },
    ],
  })),
};

export const trendData = [
  { day: 'Mon', findings: 38, critical: 12 },
  { day: 'Tue', findings: 46, critical: 15 },
  { day: 'Wed', findings: 52, critical: 18 },
  { day: 'Thu', findings: 40, critical: 14 },
  { day: 'Fri', findings: 64, critical: 22 },
  { day: 'Sat', findings: 49, critical: 19 },
  { day: 'Sun', findings: 58, critical: 25 },
];

export const donutData = [
  { name: 'Critical', value: 4, color: '#ff3d3d' },
  { name: 'High',     value: 3, color: '#ff7a1a' },
  { name: 'Medium',   value: 1, color: '#fbbf24' },
  { name: 'Low',      value: 2, color: '#00e5a0' },
];