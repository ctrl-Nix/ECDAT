export const appRoutes = {
  landing: '/',
  login: '/login',
  dashboard: '/dashboard',
};

export const riskColors = {
  CRITICAL: 'var(--risk-critical)',
  HIGH: 'var(--risk-high)',
  MEDIUM: 'var(--risk-medium)',
  LOW: 'var(--risk-low)',
};

export const CONFIDENCE_BANDS = ["VERIFIED", "PROBABLE", "UNVERIFIED"];
export const CONFIDENCE_BAND_LABELS = {
  VERIFIED: "Verified",
  PROBABLE: "Probable",
  UNVERIFIED: "Unverified",
};

export const mockScans = [
  {
    id: 101,
    repository: 'github.com/enterprise/core-banking',
    branch: 'main',
    status: 'Completed',
    findings: 42,
    date: '2026-08-20',
  },
  {
    id: 102,
    repository: 'github.com/enterprise/payments',
    branch: 'release-2.4',
    status: 'Running',
    findings: 18,
    date: '2026-08-23',
  },
  {
    id: 103,
    repository: 'github.com/enterprise/identity',
    branch: 'develop',
    status: 'Failed',
    findings: 6,
    date: '2026-08-18',
  },
];

export const mockFindings = [
  {
    id: 1,
    file: 'src/auth/legacy_login.py',
    algorithm: 'MD5',
    line: 42,
    severity: 'CRITICAL',
    risk_tier: 'CRITICAL',
    confidence: 'high',
    confidence_band: 'VERIFIED',
    confidence_score: 0.90,
    confidence_signals: ['import_resolved', 'call_site_matched', 'expected_module_confirmed', 'literal_algorithm_arg'],
    date: '2026-08-22',
    summary: 'Legacy MD5 hash used for password verification.',
  },
  {
    id: 2,
    file: 'src/utils/cert_gen.py',
    algorithm: 'RSA',
    line: 15,
    severity: 'HIGH',
    risk_tier: 'HIGH',
    confidence: 'unverified',
    confidence_band: 'PROBABLE',
    confidence_score: 0.70,
    confidence_signals: ['call_site_matched', 'rule_yaml_matched'],
    date: '2026-08-21',
    summary: 'RSA key length below 2048-bit requirement.',
  },
  {
    id: 3,
    file: 'src/api/handlers.js',
    algorithm: 'SHA-1',
    line: 88,
    severity: 'MEDIUM',
    risk_tier: 'MEDIUM',
    confidence: 'unverified',
    confidence_band: 'UNVERIFIED',
    confidence_score: 0.35,
    confidence_signals: ['dynamic_algorithm_arg'],
    date: '2026-08-20',
    summary: 'Weak hash used in token signing flow.',
  },
  {
    id: 4,
    file: 'lib/encryption.c',
    algorithm: 'AES',
    line: 112,
    severity: 'LOW',
    risk_tier: 'LOW',
    confidence: 'high',
    confidence_band: 'VERIFIED',
    confidence_score: 0.85,
    confidence_signals: ['import_resolved', 'call_site_matched'],
    date: '2026-08-19',
    summary: 'AES-128 configuration still present in legacy service.',
  },
];

