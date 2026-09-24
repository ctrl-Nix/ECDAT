import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import FindingsTable from '../../components/FindingsTable.jsx';
import api from '../../lib/api.js';

export default function FindingsPage() {
  const [scanId, setScanId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    api.get('/scans', { params: { limit: 1 } })
      .then(({ data }) => {
        if (active) setScanId(data?.scans?.[0]?.id ?? null);
      })
      .catch((requestError) => {
        if (active) setError(requestError?.response?.data?.detail || requestError.message || 'Could not load scans.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <main className="min-h-screen space-y-5 bg-void p-4 sm:p-6" style={{ background: 'var(--void)' }}>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold" style={{ color: 'var(--t1)' }}>Scan findings</h1>
        <Link to="/dashboard" className="btn-ghost">Back to dashboard</Link>
      </div>
      {loading ? <div className="card p-6 text-sm" style={{ color: 'var(--t2)' }}>Loading latest scan…</div>
        : error ? <div role="alert" className="card p-6 text-sm" style={{ color: 'var(--critical)' }}>{error}</div>
          : scanId ? <FindingsTable scanId={scanId} />
            : <div className="card p-6 text-sm" style={{ color: 'var(--t2)' }}>No scans are available yet.</div>}
    </main>
  );
}
