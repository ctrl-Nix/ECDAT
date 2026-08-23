import { useState } from 'react';
import FindingsTable from './components/FindingsTable.jsx';
import CBOMViewer from './components/CBOMViewer.jsx';
import RiskChart from './components/RiskChart.jsx';

const tabs = {
  findings: { label: 'Findings', component: <FindingsTable /> },
  cbom: { label: 'CBOM Export', component: <CBOMViewer /> },
  risk: { label: 'Risk Chart', component: <RiskChart /> },
};

export default function App() {
  const [active, setActive] = useState('findings');

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px', fontFamily: 'sans-serif' }}>
      <h1 style={{ marginBottom: '4px' }}>Crypto Discovery Dashboard</h1>
      <p style={{ color: '#47536B', marginTop: 0 }}>PS 26164 — ctrl-Nix</p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid #DFE4EC' }}>
        {Object.entries(tabs).map(([key, { label }]) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              borderBottom: active === key ? '2px solid #0F9E93' : '2px solid transparent',
              fontWeight: active === key ? 700 : 400,
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {tabs[active].component}
    </div>
  );
}
