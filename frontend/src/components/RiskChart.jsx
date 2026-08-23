import { mockFindings } from '../mockData.js';

// Day 1-2: a simple bar visualization built with plain divs, so there's
// no extra dependency to install yet. Swap this for Chart.js or Recharts
// once you're ready to install one (see the team plan's tool choice).

const tierOrder = ['Critical', 'High', 'Medium', 'Low'];
const tierColors = {
  Critical: '#B9740A',
  High: '#C2410C',
  Medium: '#0F9E93',
  Low: '#8592A8',
};

export default function RiskChart() {
  const counts = tierOrder.map((tier) => ({
    tier,
    count: mockFindings.filter((f) => f.riskTier === tier).length,
  }));
  const max = Math.max(...counts.map((c) => c.count), 1);

  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <h2>Risk Distribution</h2>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '16px', height: '160px' }}>
        {counts.map(({ tier, count }) => (
          <div key={tier} style={{ textAlign: 'center' }}>
            <div
              style={{
                height: `${(count / max) * 120}px`,
                width: '48px',
                background: tierColors[tier],
                borderRadius: '4px 4px 0 0',
                marginBottom: '6px',
              }}
            />
            <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{count}</div>
            <div style={{ fontSize: '0.75rem', color: '#47536B' }}>{tier}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
