import { useState } from 'react';
import { mockFindings } from '../mockData.js';

// Day 1-2: renders the mock findings.
// Day 3 task (per the team plan): make the severity filter actually
// useful, add a file-name filter too. A basic severity filter is
// already wired up below so Day 3 is a smaller lift.

const severityColors = {
  Critical: '#B9740A',
  High: '#C2410C',
  Medium: '#0F9E93',
  Low: '#47536B',
};

export default function FindingsTable() {
  const [severityFilter, setSeverityFilter] = useState('All');

  const filtered = severityFilter === 'All'
    ? mockFindings
    : mockFindings.filter((f) => f.severity === severityFilter);

  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <h2>Findings</h2>

      <label style={{ fontSize: '0.85rem', marginRight: '8px' }}>
        Filter by severity:
      </label>
      <select
        value={severityFilter}
        onChange={(e) => setSeverityFilter(e.target.value)}
        style={{ marginBottom: '12px' }}
      >
        <option>All</option>
        <option>Critical</option>
        <option>High</option>
        <option>Medium</option>
        <option>Low</option>
      </select>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr style={{ background: '#0B1220', color: '#EAF0F6', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>File</th>
            <th style={{ padding: '8px' }}>Line</th>
            <th style={{ padding: '8px' }}>Algorithm</th>
            <th style={{ padding: '8px' }}>Severity</th>
            <th style={{ padding: '8px' }}>Suggested fix</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((f) => (
            <tr key={f.finding_id} style={{ borderBottom: '1px solid #DFE4EC' }}>
              <td style={{ padding: '8px' }}>{f.file}</td>
              <td style={{ padding: '8px' }}>{f.line}</td>
              <td style={{ padding: '8px' }}>{f.algorithm}</td>
              <td style={{ padding: '8px', color: severityColors[f.severity], fontWeight: 600 }}>
                {f.severity}
              </td>
              <td style={{ padding: '8px' }}>{f.suggestion}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
