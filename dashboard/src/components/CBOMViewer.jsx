import { mockCbomEntry } from '../mockData.js';

// Day 1-2: just pretty-prints a sample CBOM entry so the screen exists.
// Day 4: swap this for a real fetch('/cbom/export') call once the
// backend endpoint exists.

export default function CBOMViewer() {
  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <h2>CBOM Export</h2>
      <p style={{ color: '#47536B', fontSize: '0.9rem' }}>
        CycloneDX-formatted Cryptography Bill of Materials — sample shown below.
      </p>
      <pre
        style={{
          background: '#0B1220',
          color: '#7FE0D5',
          padding: '16px',
          borderRadius: '6px',
          overflowX: 'auto',
          fontSize: '0.82rem',
        }}
      >
        {JSON.stringify(mockCbomEntry, null, 2)}
      </pre>
    </div>
  );
}
