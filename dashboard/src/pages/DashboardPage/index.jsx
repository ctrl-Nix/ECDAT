import ProjectDemoWalkthrough from '../../components/ProjectDemoWalkthrough';
import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, Bell, ChevronDown, ChevronRight, Download, FileText,
  FolderOpen, LayoutDashboard, ListFilter, LoaderCircle, Lock,
  Plus, Search, Settings, ShieldCheck, UserCircle, X, AlertTriangle,
  CheckCircle2, Terminal, Code2, Zap, Clock, GitBranch, ExternalLink,
  Cpu, RefreshCw, LogOut,
} from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, CartesianGrid, XAxis, YAxis, Legend,
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  mockFindings, mockScans, mockCbom, trendData, donutData,
} from '../../mockData.js';
import ConfidenceStamp from '../../components/ConfidenceStamp.jsx';
import api from '../../lib/api';


/* ─── helpers ─────────────────────────────────────────────────────────────── */
const STATUS_STYLE = {
  completed: 'badge-low',
  running:   'badge-critical', // Actually running should be cyan. I'll make a badge-cyan class in css, but for now fallback to inline.
  failed:    'badge-critical',
};

const STATUS_ICON = {
  completed: <CheckCircle2 className="h-3 w-3" />,
  running:   <LoaderCircle className="h-3 w-3 animate-spin" />,
  failed:    <AlertTriangle className="h-3 w-3" />,
};

function RiskBadge({ tier }) {
  const badgeClass = `badge badge-${(tier || 'LOW').toLowerCase()}`;
  return (
    <span className={badgeClass}>
      {tier}
    </span>
  );
}

function ConfidenceDot({ level }) {
  const bg = level === 'high' ? 'var(--green)' : level === 'medium' ? 'var(--medium)' : 'var(--t3)';
  return <span className="inline-block h-2 w-2 rounded-full" style={{ background: bg }} />;
}

/* ─── New Scan Modal ──────────────────────────────────────────────────────── */
function NewScanModal({ onClose }) {
  const [step, setStep] = useState('form'); // 'form' | 'scanning' | 'done'
  const [url, setUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [progress, setProgress] = useState(0);

  const handleScan = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setStep('scanning');
    for (let i = 0; i <= 100; i += 5) {
      await new Promise((r) => setTimeout(r, 80));
      setProgress(i);
    }
    setStep('done');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        className="absolute inset-0 backdrop-blur-sm"
        style={{ background: 'rgba(3, 7, 17, 0.85)' }}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97 }}
        className="relative z-10 w-full max-w-lg card-raised p-6 shadow-2xl"
      >
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold" style={{ color: 'var(--t1)' }}>New Scan</h2>
            <p className="text-sm" style={{ color: 'var(--t2)' }}>Scan a repository for cryptographic findings</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 transition-colors" style={{ color: 'var(--t3)' }} onMouseOver={e=>e.currentTarget.style.color='var(--t1)'} onMouseOut={e=>e.currentTarget.style.color='var(--t3)'}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {step === 'form' && (
          <form onSubmit={handleScan} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>Repository URL</label>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="github.com/org/repository"
                className="field"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>Branch</label>
              <input
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
                className="field"
              />
            </div>
            <div className="flex gap-2">
              {['Python', 'JavaScript', 'Java', 'Go', 'Rust', 'C/C++'].map((lang) => (
                <button key={lang} type="button"
                  className="rounded-md border px-2 py-1 text-xs transition-colors"
                  style={{ borderColor: 'var(--border)', color: 'var(--t2)' }}
                  onMouseOver={e=>{e.currentTarget.style.borderColor='var(--cyan)'; e.currentTarget.style.color='var(--cyan)'}}
                  onMouseOut={e=>{e.currentTarget.style.borderColor='var(--border)'; e.currentTarget.style.color='var(--t2)'}}
                >
                  {lang}
                </button>
              ))}
            </div>
            <div className="pt-2">
              <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2 py-2.5">
                <Terminal className="h-4 w-4" /> Start scan
              </button>
            </div>
          </form>
        )}

        {step === 'scanning' && (
          <div className="space-y-4">
            <div className="terminal p-4">
              <div style={{ color: 'var(--cyan)' }}>$ ecdat scan {url || 'github.com/enterprise/repo'}</div>
              <div style={{ color: 'var(--t3)' }}>[INFO] Cloning repository...</div>
              {progress > 20 && <div style={{ color: 'var(--t3)' }}>[INFO] Indexing source files...</div>}
              {progress > 40 && <div style={{ color: 'var(--medium)' }}>[SCAN] Running AST analysis...</div>}
              {progress > 60 && <div style={{ color: 'var(--medium)' }}>[SCAN] Scoring findings...</div>}
              {progress > 80 && <div style={{ color: 'var(--cyan)' }}>[INFO] Generating CBOM...</div>}
            </div>
            <div>
              <div className="mb-2 flex justify-between text-xs" style={{ color: 'var(--t2)' }}>
                <span>Scanning...</span><span className="num">{progress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          </div>
        )}

        {step === 'done' && (
          <div className="space-y-4 text-center py-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full" style={{ background: 'var(--green-10)', color: 'var(--green)' }}>
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <div>
              <div className="text-lg font-semibold" style={{ color: 'var(--t1)' }}>Scan complete</div>
              <div className="text-sm mt-1 num" style={{ color: 'var(--t2)' }}>3 findings detected · 1 critical</div>
            </div>
            <button onClick={onClose} className="btn-primary w-full mt-4">
              View results
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}

/* ─── Finding detail panel ────────────────────────────────────────────────── */
function FindingPanel({ finding, onClose }) {
  if (!finding) return null;
  return (
    <motion.div
      initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 26, stiffness: 260 }}
      className="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col border-l shadow-2xl"
      style={{ borderColor: 'var(--border)', background: 'var(--surface-r)' }}
    >
      <div className="flex items-center justify-between border-b px-5 py-4" style={{ borderColor: 'var(--border)' }}>
        <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Finding Detail</div>
        <button onClick={onClose} className="rounded-lg p-1.5 transition-colors" style={{ color: 'var(--t3)' }} onMouseOver={e=>e.currentTarget.style.color='var(--t1)'} onMouseOut={e=>e.currentTarget.style.color='var(--t3)'}>
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-start gap-3">
          <RiskBadge tier={finding.risk_tier} />
          {finding.quantum_vulnerable && (
            <span className="badge badge-quantum">
              <Zap className="h-3 w-3 mr-1" /> Quantum risk
            </span>
          )}
        </div>

        <div>
          <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--t3)' }}>Algorithm</div>
          <div className="mono text-lg font-bold" style={{ color: 'var(--t1)' }}>{finding.algorithm}</div>
        </div>

        <div className="card p-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <span style={{ color: 'var(--t2)' }}>File</span>
            <span className="mono text-xs" style={{ color: 'var(--t1)' }}>{finding.file}</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--t2)' }}>Line</span>
            <span className="num" style={{ color: 'var(--t1)' }}>{finding.line}</span>
          </div>
          <div className="flex justify-between items-center">
            <span style={{ color: 'var(--t2)' }}>Confidence</span>
            <ConfidenceStamp
              band={finding.confidence_band || (finding.confidence === 'high' ? 'VERIFIED' : 'UNVERIFIED')}
              score={finding.confidence_score}
              signals={finding.confidence_signals}
            />
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--t2)' }}>Classical broken</span>
            <span style={{ color: finding.classical_broken ? 'var(--critical)' : 'var(--green)' }}>
              {finding.classical_broken ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--t2)' }}>Quantum vulnerable</span>
            <span style={{ color: finding.quantum_vulnerable ? 'var(--purple)' : 'var(--green)' }}>
              {finding.quantum_vulnerable ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--t3)' }}>Risk Analysis</div>
          <div className="card p-4 text-sm leading-relaxed" style={{ color: 'var(--t2)' }}>
            {finding.summary}
          </div>
        </div>

        {finding.replacement && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--t3)' }}>Recommended Replacement</div>
            <div className="flex items-center gap-2 rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(0,229,160,0.2)', background: 'var(--green-10)' }}>
              <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: 'var(--green)' }} />
              <span className="mono text-sm" style={{ color: 'var(--green)' }}>{finding.replacement}</span>
            </div>
          </div>
        )}
      </div>
      <div className="border-t p-4 flex gap-3" style={{ borderColor: 'var(--border)' }}>
        <button className="btn-ghost flex-1 py-2.5 text-center flex justify-center">Copy finding</button>
        <button className="btn-primary flex-1 py-2.5 text-center flex justify-center">Get remediation</button>
      </div>
    </motion.div>
  );
}

/* ─── Sidebar ────────────────────────────────────────────────────────────── */
const NAV = [
  { id: 'overview',    label: 'Overview',      icon: LayoutDashboard },
  { id: 'live',        label: 'Live Scan',      icon: Terminal },
  { id: 'findings',    label: 'Findings',       icon: AlertTriangle },
  { id: 'scans',       label: 'Scan History',   icon: Activity },
  { id: 'cbom',        label: 'CBOM Library',   icon: FolderOpen },
  { id: 'reports',     label: 'Reports',        icon: FileText },
  { id: 'settings',    label: 'Settings',       icon: Settings },
];

/* ─── Overview Tab ───────────────────────────────────────────────────────── */
function OverviewTab({ onNewScan, onSelectFinding }) {
  const total = donutData.reduce((s, d) => s + d.value, 0);

  const CUSTOM_TOOLTIP = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="card-raised px-3 py-2 text-sm shadow-lg">
        <div className="font-semibold" style={{ color: 'var(--t1)' }}>{payload[0].name}</div>
        <div className="num" style={{ color: 'var(--t2)' }}>{payload[0].value} findings</div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { title: 'Total Findings', value: mockFindings.length, sub: `${mockFindings.filter(f => f.risk_tier === 'CRITICAL').length} critical`, accent: 'var(--t1)', icon: AlertTriangle },
          { title: 'Active Scans', value: mockScans.filter(s => s.status === 'running').length, sub: 'Running now', accent: 'var(--cyan)', icon: Activity },
          { title: 'Repositories', value: mockScans.length, sub: 'Indexed', accent: 'var(--t1)', icon: Code2 },
          { title: 'Compliance Score', value: '87%', sub: 'NIST PQC ready', accent: 'var(--green)', icon: ShieldCheck },
        ].map((card, i) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="card p-5"
          >
            <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>
              <span>{card.title}</span>
              <card.icon className="h-4 w-4" />
            </div>
            <div className="mt-4 text-3xl font-black num" style={{ color: card.accent }}>{card.value}</div>
            <div className="mt-1 text-xs num" style={{ color: 'var(--t2)' }}>{card.sub}</div>
          </motion.div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid gap-6 xl:grid-cols-[1fr_1.6fr]">
        {/* Donut */}
        <div className="card p-5">
          <div className="mb-4 text-sm font-semibold" style={{ color: 'var(--t1)' }}>Risk distribution</div>
          <div className="relative h-52">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={donutData} dataKey="value" innerRadius={54} outerRadius={82} paddingAngle={3}>
                  {donutData.map((entry) => <Cell key={entry.name} fill={entry.color} strokeWidth={0} />)}
                </Pie>
                <Tooltip content={<CUSTOM_TOOLTIP />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-2xl font-black num" style={{ color: 'var(--t1)' }}>{total}</div>
              <div className="text-xs uppercase tracking-wider font-semibold" style={{ color: 'var(--t3)' }}>findings</div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {donutData.map((d) => (
              <div key={d.name} className="flex items-center gap-2 text-xs" style={{ color: 'var(--t2)' }}>
                <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ background: d.color }} />
                <span className="num">{d.name} — {d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bar chart */}
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Finding trends</div>
            <div className="flex gap-1">
              {['7d', '30d', 'All'].map((f) => (
                <button key={f}
                  className="rounded-full px-2.5 py-1 text-xs font-medium transition-colors"
                  style={{
                    background: f === '7d' ? 'var(--cyan-10)' : 'transparent',
                    color: f === '7d' ? 'var(--cyan)' : 'var(--t2)',
                  }}>
                  {f}
                </button>
              ))}
            </div>
          </div>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData} barGap={4}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="day" stroke="var(--border-s)" tick={{ fontSize: 11, fill: 'var(--t2)', fontFamily: 'JetBrains Mono' }} />
                <YAxis stroke="var(--border-s)" tick={{ fontSize: 11, fill: 'var(--t2)', fontFamily: 'JetBrains Mono' }} />
                <Tooltip content={<CUSTOM_TOOLTIP />} />
                <Bar dataKey="findings" fill="var(--cyan)" radius={[4, 4, 0, 0]} name="Total" fillOpacity={0.85} />
                <Bar dataKey="critical" fill="var(--critical)" radius={[4, 4, 0, 0]} name="Critical" fillOpacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent findings */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Recent findings</div>
          <button className="text-xs" style={{ color: 'var(--cyan)' }}>View all →</button>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Risk</th>
                <th>Algorithm</th>
                <th>File</th>
                <th>Quantum</th>
                <th>Date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {mockFindings.slice(0, 5).map((f) => (
                <tr key={f.id} onClick={() => onSelectFinding(f)} className="cursor-pointer">
                  <td><RiskBadge tier={f.risk_tier} /></td>
                  <td className="mono font-semibold" style={{ color: 'var(--t1)' }}>{f.algorithm}</td>
                  <td className="mono" style={{ color: 'var(--t2)' }}>{f.file}:{f.line}</td>
                  <td>
                    {f.quantum_vulnerable
                      ? <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--purple)' }}><Zap className="h-3 w-3" />Yes</span>
                      : <span className="text-xs" style={{ color: 'var(--t3)' }}>No</span>}
                  </td>
                  <td className="text-xs" style={{ color: 'var(--t2)' }}>{f.date}</td>
                  <td className="text-right">
                    <ChevronRight className="h-4 w-4 inline" style={{ color: 'var(--t3)' }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── Findings Tab ───────────────────────────────────────────────────────── */
function FindingsTab({ onSelectFinding }) {
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('All');
  const [quantumOnly, setQuantumOnly] = useState(false);

  const filtered = useMemo(() => {
    return mockFindings.filter((f) => {
      const matchTier = tierFilter === 'All' || f.risk_tier === tierFilter;
      const matchSearch = !search || f.file.toLowerCase().includes(search.toLowerCase())
        || f.algorithm.toLowerCase().includes(search.toLowerCase());
      const matchQ = !quantumOnly || f.quantum_vulnerable;
      return matchTier && matchSearch && matchQ;
    });
  }, [search, tierFilter, quantumOnly]);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm" style={{ borderColor: 'var(--border)', background: 'var(--surface-h)' }}>
          <Search className="h-4 w-4 shrink-0" style={{ color: 'var(--t3)' }} />
          <input
            value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search file or algorithm…"
            className="bg-transparent text-sm focus:outline-none w-52"
            style={{ color: 'var(--t1)' }}
          />
        </div>
        <div className="flex items-center gap-1 rounded-xl border p-1" style={{ borderColor: 'var(--border)', background: 'var(--surface-h)' }}>
          {['All', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((t) => (
            <button key={t}
              onClick={() => setTierFilter(t)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
              style={{
                background: tierFilter === t ? 'var(--cyan-10)' : 'transparent',
                color: tierFilter === t ? 'var(--cyan)' : 'var(--t2)',
              }}>
              {t}
            </button>
          ))}
        </div>
        <button
          onClick={() => setQuantumOnly((v) => !v)}
          className="flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-medium transition-colors badge"
          style={{
             borderColor: quantumOnly ? 'rgba(157,110,248,0.25)' : 'var(--border)',
             background: quantumOnly ? 'var(--purple-10)' : 'transparent',
             color: quantumOnly ? 'var(--purple)' : 'var(--t2)'
          }}>
          <Zap className="h-3.5 w-3.5" /> Quantum only
        </button>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(mockCbom, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'ecdat-cbom.json'; a.click();
          }}
          className="btn-ghost ml-auto flex items-center gap-2">
          <Download className="h-3.5 w-3.5" /> Export CBOM
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="data-table">
          <thead>
            <tr>
              <th>Risk Tier</th>
              <th>Algorithm</th>
              <th>File</th>
              <th>Line</th>
              <th>Confidence</th>
              <th>Quantum</th>
              <th>Date</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={8} className="text-center py-8 text-sm" style={{ color: 'var(--t3)' }}>No findings match filters</td></tr>
            )}
            {filtered.map((f) => (
              <motion.tr
                key={f.id}
                onClick={() => onSelectFinding(f)}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="cursor-pointer"
              >
                <td><RiskBadge tier={f.risk_tier} /></td>
                <td className="mono font-semibold" style={{ color: 'var(--t1)' }}>{f.algorithm}</td>
                <td className="mono" style={{ color: 'var(--t1)' }}>{f.file}</td>
                <td className="num" style={{ color: 'var(--t2)' }}>{f.line}</td>
                <td>
                  <ConfidenceStamp
                    band={f.confidence_band || (f.confidence === 'high' ? 'VERIFIED' : 'UNVERIFIED')}
                    score={f.confidence_score}
                    signals={f.confidence_signals}
                  />
                </td>
                <td>
                  {f.quantum_vulnerable
                    ? <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--purple)' }}><Zap className="h-3 w-3" />Yes</span>
                    : <span className="text-xs" style={{ color: 'var(--t3)' }}>—</span>}
                </td>
                <td className="text-xs num" style={{ color: 'var(--t2)' }}>{f.date}</td>
                <td className="text-right">
                  <ChevronRight className="h-4 w-4 inline" style={{ color: 'var(--t3)' }} />
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-right num" style={{ color: 'var(--t3)' }}>{filtered.length} of {mockFindings.length} findings</div>
    </div>
  );
}

/* ─── Scan History Tab ───────────────────────────────────────────────────── */
function ScansTab({ onNewScan }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={onNewScan} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" /> New scan
        </button>
      </div>
      <div className="space-y-3">
        {mockScans.map((scan, i) => (
          <motion.div
            key={scan.id}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="card flex items-center justify-between p-5 cursor-pointer"
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl shrink-0" style={{ background: 'var(--surface-h)', color: 'var(--t2)' }}>
                <Code2 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--t1)' }}>
                  {scan.repository}
                  <ExternalLink className="h-3 w-3" style={{ color: 'var(--t3)' }} />
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs num" style={{ color: 'var(--t2)' }}>
                  <span className="flex items-center gap-1"><GitBranch className="h-3 w-3" />{scan.branch}</span>
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{scan.duration}</span>
                  <span>{scan.date}</span>
                </div>
                <div className="mt-2 flex gap-2">
                  {scan.languages.map((l) => (
                    <span key={l} className="rounded-full border px-2 py-0.5 text-[10px]" style={{ borderColor: 'var(--border)', color: 'var(--t2)' }}>{l}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-5 shrink-0">
              <div className="text-right">
                <div className="text-lg font-black num" style={{ color: scan.critical > 0 ? 'var(--critical)' : 'var(--t1)' }}>{scan.findings}</div>
                <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>findings</div>
              </div>
              <span className={`badge ${STATUS_STYLE[scan.status] || 'badge-low'} flex gap-1.5 items-center`}>
                {STATUS_ICON[scan.status]} {scan.status}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

/* ─── CBOM Tab ───────────────────────────────────────────────────────────── */
function CbomTab() {
  const handleExport = () => {
    const blob = new Blob([JSON.stringify(mockCbom, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'ecdat-cbom.json'; a.click();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>CBOM Library</div>
          <div className="text-xs mt-0.5 num" style={{ color: 'var(--t2)' }}>CycloneDX 1.6 — {mockCbom.components.length} cryptographic assets</div>
        </div>
        <button onClick={handleExport} className="btn-primary flex items-center gap-2">
          <Download className="h-4 w-4" /> Export CBOM JSON
        </button>
      </div>

      {/* CBOM metadata */}
      <div className="card p-5">
        <div className="mb-4 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>Metadata</div>
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          {[
            ['Format', 'CycloneDX'], ['Spec Version', '1.6'], ['Serial', mockCbom.serialNumber],
            ['Generated', mockCbom.metadata.timestamp], ['Tool', 'ECDAT v1.0.0 by Port53'],
          ].map(([k, v]) => (
            <div key={k} className="flex flex-col gap-0.5">
              <span className="text-xs" style={{ color: 'var(--t2)' }}>{k}</span>
              <span className="mono text-xs break-all" style={{ color: 'var(--t1)' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Components */}
      <div className="card overflow-hidden">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Algorithm</th>
              <th>File</th>
              <th>Risk</th>
              <th>Quantum</th>
            </tr>
          </thead>
          <tbody>
            {mockFindings.map((f, i) => (
              <tr key={f.id}>
                <td className="mono num" style={{ color: 'var(--t3)' }}>{String(i + 1).padStart(2, '0')}</td>
                <td className="mono font-semibold" style={{ color: 'var(--t1)' }}>{f.algorithm}</td>
                <td className="mono" style={{ color: 'var(--t1)' }}>{f.file}</td>
                <td><RiskBadge tier={f.risk_tier} /></td>
                <td>
                  {f.quantum_vulnerable ? <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--purple)' }}><Zap className="h-3 w-3" />Yes</span> : <span className="text-xs" style={{ color: 'var(--t3)' }}>No</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Reports Tab ────────────────────────────────────────────────────────── */
function ReportsTab() {
  const reports = [
    { name: 'Executive Summary — August 2026', type: 'PDF', size: '284 KB', date: '2026-08-24', status: 'Ready' },
    { name: 'NIST PQC Compliance Report', type: 'PDF', size: '512 KB', date: '2026-08-22', status: 'Ready' },
    { name: 'CycloneDX CBOM Export', type: 'JSON', size: '48 KB', date: '2026-08-24', status: 'Ready' },
    { name: 'Full Findings Export', type: 'CSV', size: '18 KB', date: '2026-08-20', status: 'Ready' },
  ];

  const handleDownload = (report) => {
    if (report.type === 'JSON') {
      const blob = new Blob([JSON.stringify(mockCbom, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob); const a = document.createElement('a');
      a.href = url; a.download = 'ecdat-cbom.json'; a.click();
    } else if (report.type === 'CSV') {
      const header = 'ID,File,Algorithm,Line,Risk Tier,Quantum,Date\n';
      const rows = mockFindings.map(f => `${f.id},${f.file},${f.algorithm},${f.line},${f.risk_tier},${f.quantum_vulnerable},${f.date}`).join('\n');
      const blob = new Blob([header + rows], { type: 'text/csv' });
      const url = URL.createObjectURL(blob); const a = document.createElement('a');
      a.href = url; a.download = 'ecdat-findings.csv'; a.click();
    } else if (report.type === 'PDF') {
      const isExec = report.name.includes('Executive');
      const content = isExec
        ? `=================================================================\n` +
          `ECDAT - EXECUTIVE CRYPTOGRAPHIC AUDIT REPORT\n` +
          `=================================================================\n\n` +
          `Date: ${report.date}\n` +
          `Organization: Enterprise Cryptographic Discovery & Quantum Risk\n` +
          `Audit Status: COMPLIANCE ACTION REQUIRED\n\n` +
          `EXECUTIVE SUMMARY:\n` +
          `- Total Cryptographic Findings: ${mockFindings.length}\n` +
          `- Critical Severity Flaws: ${mockFindings.filter(f => f.risk_tier === 'CRITICAL').length}\n` +
          `- High Severity Flaws: ${mockFindings.filter(f => f.risk_tier === 'HIGH').length}\n` +
          `- Quantum-Vulnerable Assets: ${mockFindings.filter(f => f.quantum_vulnerable).length}\n\n` +
          `DETAILED FINDINGS BREAKDOWN:\n` +
          mockFindings.map(f => `  * [${f.risk_tier}] ${f.algorithm} in ${f.file}:${f.line} (Quantum Risk: ${f.quantum_vulnerable ? 'YES' : 'NO'})`).join('\n') +
          `\n\nGenerated by ECDAT (Enterprise Cryptographic Assessment Tool)`
        : `=================================================================\n` +
          `NIST POST-QUANTUM CRYPTOGRAPHY (PQC) COMPLIANCE REPORT\n` +
          `=================================================================\n\n` +
          `Evaluation Date: ${report.date}\n` +
          `Framework Compliance: NIST IR 8413 / FIPS 203 (ML-KEM) & FIPS 204 (ML-DSA)\n\n` +
          `REMEDIATION ACTION PLAN:\n` +
          `1. Replace deprecated MD5 / SHA-1 digest usage with SHA-256 / SHA-3.\n` +
          `2. Upgrade classical RSA-1024 / ECC P-256 to Quantum-Resistant ML-KEM / ML-DSA.\n` +
          `3. Expand AES key sizes to 256 bits for long-term data protection.\n\n` +
          `AUDITED ASSETS:\n` +
          mockFindings.map(f => `  * ${f.file}:${f.line} -> Current: ${f.algorithm} (Recommended Replacement: ${f.replacement || 'ML-KEM-768'})`).join('\n') +
          `\n\nGenerated by ECDAT Compliance Engine`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${isExec ? 'ecdat-executive-summary' : 'nist-pqc-compliance-report'}.txt`;
      a.click();
    }
  };

  return (
    <div className="space-y-4">
      {reports.map((r, i) => (
        <motion.div
          key={r.name}
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="card flex items-center justify-between p-5"
        >
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl text-xs font-bold" style={{ background: 'var(--surface-h)', color: 'var(--t2)' }}>
              {r.type}
            </div>
            <div>
              <div className="text-sm font-medium" style={{ color: 'var(--t1)' }}>{r.name}</div>
              <div className="text-xs mt-0.5 num" style={{ color: 'var(--t2)' }}>{r.size} · {r.date}</div>
            </div>
          </div>
          <button onClick={() => handleDownload(r)} className="btn-ghost flex items-center gap-2">
            <Download className="h-3.5 w-3.5" /> Download
          </button>
        </motion.div>
      ))}
    </div>
  );
}

/* ─── Settings Tab ───────────────────────────────────────────────────────── */
function SettingsTab({ onLogout }) {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="card p-6 space-y-4">
        <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>LLM Remediation</div>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>Google Gemini API Key</label>
            <input value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIza…" className="field mono" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t3)' }}>Provider</label>
            <select className="field">
              {['Gemini (Google)', 'OpenAI', 'Groq (Llama)', 'Grok (xAI)', 'Ollama (Local)'].map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-primary w-full sm:w-auto mt-2" style={{ background: saved ? 'var(--green)' : 'var(--cyan)' }}>
            {saved ? <span className="flex items-center gap-2 justify-center"><CheckCircle2 className="h-4 w-4" /> Saved!</span> : 'Save settings'}
          </button>
        </form>
      </div>

      <div className="card p-6 space-y-3">
        <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Account</div>
        <div className="text-sm" style={{ color: 'var(--t2)' }}>analyst@ecdat.local · Analyst role</div>
        <button onClick={onLogout}
          className="flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-colors"
          style={{ borderColor: 'rgba(255,61,61,0.3)', background: 'rgba(255,61,61,0.06)', color: 'var(--critical)' }}>
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>

      <div className="card p-6 space-y-3">
        <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Backend connection</div>
        <div className="flex items-center gap-2 text-xs mono" style={{ color: 'var(--t1)' }}>
          <span className="live-ping relative flex h-2 w-2 rounded-full" style={{ background: 'var(--green)' }} />
          API: http://localhost:8000
        </div>
        <div className="text-xs num" style={{ color: 'var(--t3)' }}>Scan engine v1.0.0 · DB: ecdat.db</div>
      </div>
    </div>
  );
}

/* ─── Live Scan Tab ──────────────────────────────────────────────────────── */
// Maps a backend FindingOut (with nested risk_assessment) to the flat shape
// the table + FindingPanel expect.
function mapLiveFinding(f, scan) {
  const ra = f.risk_assessment || {};
  return {
    id: f.id,
    file: f.file,
    line: f.line,
    algorithm: f.algorithm,
    language: f.language,
    risk_tier: f.risk_tier,
    confidence: f.confidence,
    quantum_vulnerable: ra.quantum_vulnerable ?? false,
    classical_broken: ra.classical_broken ?? false,
    replacement: ra.recommended_replacement ?? null,
    summary: f.risk_reason || '—',
    date: scan?.started_at ? new Date(scan.started_at).toLocaleString() : '',
  };
}

const TIER_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, UNSCORED: 4 };

function LiveScanTab({ onSelectFinding }) {
  const [status, setStatus] = useState('idle'); // idle | loading | success | empty | error
  const [scan, setScan] = useState(null);
  const [summary, setSummary] = useState(null);
  const [findings, setFindings] = useState([]);
  const [error, setError] = useState(null);

  const fetchLive = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      // Newest scan first, then its full detail (findings + risk summary).
      const list = await api.get('/scans', { params: { limit: 1 } });
      const latest = list.data?.scans?.[0];
      if (!latest) {
        setStatus('empty');
        return;
      }
      const detail = await api.get(`/scans/${latest.id}`);
      const s = detail.data.scan;
      const mapped = (detail.data.findings || [])
        .map((f) => mapLiveFinding(f, s))
        .sort((a, b) => (TIER_ORDER[a.risk_tier] ?? 9) - (TIER_ORDER[b.risk_tier] ?? 9));
      setScan(s);
      setSummary(detail.data.summary || null);
      setFindings(mapped);
      setStatus('success');
    } catch (err) {
      const msg = err?.response?.status
        ? `API error ${err.response.status}: ${err.response.data?.detail || 'request failed'}`
        : `Cannot reach the backend (${err.message}). Is the stack running (docker compose up)?`;
      setError(msg);
      setStatus('error');
    }
  }, []);

  const TIERS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  return (
    <div className="space-y-5">
      {/* Header + fetch button */}
      <div className="card p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Live scan from the database</div>
          <div className="text-xs mt-1 num" style={{ color: 'var(--t2)' }}>
            Fetches the most recent scan persisted in the PostgreSQL container — findings + risk assessments, no mock data.
          </div>
        </div>
        <button
          onClick={fetchLive}
          disabled={status === 'loading'}
          className="btn-primary flex items-center gap-2"
        >
          {status === 'loading'
            ? <><LoaderCircle className="h-4 w-4 animate-spin" /> Fetching…</>
            : <><RefreshCw className="h-4 w-4" /> Fetch live scan</>}
        </button>
      </div>

      {status === 'idle' && (
        <div className="card p-8 text-center text-sm" style={{ color: 'var(--t3)' }}>
          Click <span style={{ color: 'var(--cyan)' }}>Fetch live scan</span> to load the latest results from the container database.
        </div>
      )}

      {status === 'error' && (
        <div className="card p-5 flex items-start gap-3" style={{ borderColor: 'rgba(255,61,61,0.25)' }}>
          <AlertTriangle className="h-5 w-5 shrink-0" style={{ color: 'var(--critical)' }} />
          <div className="text-sm" style={{ color: 'var(--critical)' }}>{error}</div>
        </div>
      )}

      {status === 'empty' && (
        <div className="card p-8 text-center text-sm" style={{ color: 'var(--t3)' }}>
          No scans found in the database yet. Run a scan first, then fetch again.
        </div>
      )}

      {status === 'success' && (
        <>
          {/* Scan meta + summary chips */}
          <div className="card p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-sm" style={{ color: 'var(--t2)' }}>
              <span className={`badge ${STATUS_STYLE[scan?.status] || 'badge-low'} flex gap-1.5 items-center`}>
                {STATUS_ICON[scan?.status]} {scan?.status}
              </span>
              <span className="num">Scan #{scan?.id}</span>
              {scan?.started_at && <span className="num">{new Date(scan.started_at).toLocaleString()}</span>}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {TIERS.map((t) => (
                <span key={t} className={`badge badge-${t.toLowerCase()}`}>
                  {t} {summary?.[t] ?? 0}
                </span>
              ))}
              <span className="text-xs num" style={{ color: 'var(--t3)' }}>· {summary?.total ?? findings.length} total</span>
            </div>
          </div>

          {/* Findings table */}
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Risk Tier</th>
                    <th>Algorithm</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Lang</th>
                    <th>Classical</th>
                    <th>Quantum</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {findings.length === 0 && (
                    <tr><td colSpan={8} className="text-center py-8 text-sm" style={{ color: 'var(--t3)' }}>Scan completed with no findings.</td></tr>
                  )}
                  {findings.map((f) => (
                    <tr key={f.id} onClick={() => onSelectFinding(f)} className="cursor-pointer">
                      <td><RiskBadge tier={f.risk_tier} /></td>
                      <td className="mono font-semibold" style={{ color: 'var(--t1)' }}>{f.algorithm}</td>
                      <td className="mono" style={{ color: 'var(--t1)' }}>{f.file}</td>
                      <td className="num" style={{ color: 'var(--t2)' }}>{f.line}</td>
                      <td className="text-xs" style={{ color: 'var(--t2)' }}>{f.language}</td>
                      <td>
                        {f.classical_broken
                          ? <span className="text-xs" style={{ color: 'var(--critical)' }}>Broken</span>
                          : <span className="text-xs" style={{ color: 'var(--t3)' }}>—</span>}
                      </td>
                      <td>
                        {f.quantum_vulnerable
                          ? <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--purple)' }}><Zap className="h-3 w-3" />Yes</span>
                          : <span className="text-xs" style={{ color: 'var(--t3)' }}>—</span>}
                      </td>
                      <td className="text-right"><ChevronRight className="h-4 w-4 inline" style={{ color: 'var(--t3)' }} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Main DashboardPage ─────────────────────────────────────────────────── */
export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [showNewScan, setShowNewScan] = useState(false);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, title: 'Critical Risk Alert', desc: 'RSA-1024 vulnerability detected in auth_service.py', time: '10m ago', unread: true, type: 'critical' },
    { id: 2, title: 'Scan Complete', desc: 'Scan finished for repo enterprise/auth-service', time: '1h ago', unread: true, type: 'success' },
    { id: 3, title: 'CBOM Export Ready', desc: 'CycloneDX 1.6 report compiled successfully', time: '3h ago', unread: false, type: 'info' },
  ]);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = useCallback(() => {
    logout();
    navigate('/');
  }, [logout, navigate]);

  const tabProps = {
    onSelectFinding: setSelectedFinding,
    onNewScan: () => setShowNewScan(true),
    onLogout: handleLogout,
  };

  const TAB_CONTENT = {
    overview: <OverviewTab {...tabProps} />,
    live:     <LiveScanTab onSelectFinding={setSelectedFinding} />,
    findings: <FindingsTab {...tabProps} />,
    scans:    <ScansTab {...tabProps} />,
    cbom:     <CbomTab />,
    reports:  <ReportsTab />,
    settings: <SettingsTab {...tabProps} />,
  };

  return (
    <div className="min-h-screen bg-void" style={{ background: 'var(--void)' }}>

      {/* Header */}
      <header className="sticky top-0 z-30 border-b backdrop-blur-md" style={{ borderColor: 'var(--border)', background: 'var(--surface)', opacity: 0.95 }}>
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(v => !v)} className="rounded-lg p-1.5 lg:hidden" style={{ color: 'var(--t3)' }}>
              <LayoutDashboard className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl" style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-semibold leading-none" style={{ color: 'var(--t1)' }}>ECDAT</div>
                <div className="text-[10px] uppercase tracking-widest font-bold" style={{ color: 'var(--t3)' }}>Dashboard</div>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="hidden items-center gap-2 rounded-xl border px-3 py-2 text-sm md:flex" style={{ borderColor: 'var(--border)', background: 'var(--surface-h)', color: 'var(--t2)' }}>
            <Search className="h-4 w-4" style={{ color: 'var(--t3)' }} />
            <span>Search findings, scans…</span>
            <span className="ml-2 rounded border px-1.5 py-0.5 text-[10px]" style={{ borderColor: 'var(--border-s)', color: 'var(--t3)' }}>⌘K</span>
          </div>

          <div className="flex items-center gap-3">
            <ProjectDemoWalkthrough/>
            <div className="relative">
              <button
                onClick={() => setNotificationsOpen(v => !v)}
                className="relative rounded-full border p-2 transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--t2)' }}
                onMouseOver={e=>e.currentTarget.style.color='var(--t1)'}
                onMouseOut={e=>e.currentTarget.style.color='var(--t2)'}
              >
                <Bell className="h-4 w-4" />
                {notifications.some(n => n.unread) && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full" style={{ background: 'var(--critical)' }} />
                )}
              </button>

              <AnimatePresence>
                {notificationsOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 top-12 z-50 w-80 rounded-2xl border p-4 shadow-2xl backdrop-blur-md"
                    style={{ borderColor: 'var(--border)', background: 'var(--surface-r)' }}
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-sm font-semibold" style={{ color: 'var(--t1)' }}>Notifications</span>
                      <button
                        onClick={() => setNotifications(ns => ns.map(n => ({ ...n, unread: false })))}
                        className="text-xs hover:underline" style={{ color: 'var(--cyan)' }}
                      >
                        Mark all read
                      </button>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {notifications.map(n => (
                        <div key={n.id} className="rounded-xl border p-3 text-xs space-y-1" style={{ borderColor: 'var(--border)', background: n.unread ? 'var(--cyan-10)' : 'var(--surface-h)' }}>
                          <div className="flex items-center justify-between font-semibold" style={{ color: 'var(--t1)' }}>
                            <span>{n.title}</span>
                            <span className="text-[10px] num" style={{ color: 'var(--t3)' }}>{n.time}</span>
                          </div>
                          <p style={{ color: 'var(--t2)' }}>{n.desc}</p>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <button
              onClick={() => setShowNewScan(true)}
              className="btn-primary hidden items-center gap-2 sm:flex">
              <Plus className="h-4 w-4" /> New scan
            </button>
            <div className="flex items-center gap-2 rounded-full border px-2 py-1.5" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
              <UserCircle className="h-6 w-6" style={{ color: 'var(--t3)' }} />
              <div className="hidden text-left sm:block">
                <div className="text-xs font-medium" style={{ color: 'var(--t1)' }}>{user?.role || 'Analyst'}</div>
                <div className="text-[10px]" style={{ color: 'var(--t2)' }}>{user?.email || 'analyst@ecdat.local'}</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <AnimatePresence>
          {(sidebarOpen) && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-20 lg:hidden"
              style={{ background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(4px)' }}
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        <aside className={`
          fixed top-16 z-20 h-[calc(100vh-64px)] w-56 border-r p-4 backdrop-blur-md transition-transform lg:sticky lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `} style={{ borderColor: 'var(--border)', background: 'var(--surface)', opacity: 0.95 }}>
          <nav className="space-y-1">
            {NAV.map(({ id, label, icon: Icon }) => (
              <button key={id}
                onClick={() => { setActiveTab(id); setSidebarOpen(false); }}
                className={`nav-item ${activeTab === id ? 'active' : ''}`}>
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-6 border-t pt-4" style={{ borderColor: 'var(--border)' }}>
            <button onClick={() => setShowNewScan(true)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border py-2.5 text-sm font-semibold transition-colors"
              style={{ borderColor: 'var(--cyan-20)', background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
              <Plus className="h-4 w-4" /> New scan
            </button>
          </div>

          <div className="absolute bottom-4 left-4 right-4">
            <div className="rounded-xl border p-3 text-xs space-y-1" style={{ borderColor: 'var(--border)', background: 'var(--surface-h)', color: 'var(--t3)' }}>
              <div className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--green)' }} />API connected</div>
              <div className="num">ECDAT v1.0.0</div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:ml-0">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold capitalize" style={{ color: 'var(--t1)' }}>
                {NAV.find(n => n.id === activeTab)?.label}
              </h1>
              <div className="mt-0.5 text-xs num" style={{ color: 'var(--t2)' }}>
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </div>
            </div>
            <button onClick={() => window.location.reload()} className="btn-ghost p-2">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {TAB_CONTENT[activeTab]}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showNewScan && <NewScanModal onClose={() => setShowNewScan(false)} />}
      </AnimatePresence>

      <AnimatePresence>
        {selectedFinding && (
          <FindingPanel finding={selectedFinding} onClose={() => setSelectedFinding(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
