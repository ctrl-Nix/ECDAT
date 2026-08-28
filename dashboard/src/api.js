import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'ecdat-secret-key-dev';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  timeout: 10000,
});

/** Check backend health status */
export async function checkHealth() {
  try {
    const res = await apiClient.get('/health');
    return res.data;
  } catch (err) {
    console.warn('Backend health check offline:', err.message);
    return { status: 'offline', version: '1.0.0-mock' };
  }
}

/** Trigger a new scan */
export async function createScan(targetPath, repoName = null, repoUrl = null) {
  try {
    const res = await apiClient.post('/scans', {
      target_path: targetPath,
      repo_name: repoName,
      repo_url: repoUrl,
    });
    return res.data;
  } catch (err) {
    console.warn('Create scan API fallback:', err.message);
    return { scan_id: Math.floor(Math.random() * 1000) + 10, status: 'running' };
  }
}

/** Get list of scans */
export async function fetchScans(limit = 50) {
  try {
    const res = await apiClient.get('/scans', { params: { limit } });
    return res.data;
  } catch (err) {
    console.warn('Fetch scans API fallback:', err.message);
    return null;
  }
}

/** Get scan details with findings */
export async function fetchScanDetails(scanId, riskTier = null) {
  try {
    const params = riskTier && riskTier !== 'All' ? { risk_tier: riskTier } : {};
    const res = await apiClient.get(`/scans/${scanId}`, { params });
    return res.data;
  } catch (err) {
    console.warn(`Fetch scan ${scanId} details fallback:`, err.message);
    return null;
  }
}

/** Get CBOM CycloneDX export for a scan */
export async function fetchCbom(scanId) {
  try {
    const res = await apiClient.get(`/scans/${scanId}/cbom`);
    return res.data;
  } catch (err) {
    console.warn(`Fetch CBOM for scan ${scanId} fallback:`, err.message);
    return null;
  }
}

/** Get remediation guidance for a specific finding */
export async function fetchRemediation(scanId, findingId) {
  try {
    const res = await apiClient.get(`/scans/${scanId}/remediation/${findingId}`);
    return res.data;
  } catch (err) {
    console.warn(`Fetch remediation fallback:`, err.message);
    return {
      finding_id: findingId,
      recommendation: 'Replace algorithm with quantum-resistant alternative (ML-KEM / SHA-256)',
      source: 'Deterministic Fallback Rule',
    };
  }
}

export default apiClient;
