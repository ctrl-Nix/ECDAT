import { useMemo, useState } from 'react';
import { Bell, ChevronDown, LayoutDashboard, Search, ShieldCheck, Download, Plus, Activity, Settings, ListFilter, FileText, FolderOpen, UserCircle, Lock } from 'lucide-react';
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, CartesianGrid, XAxis, YAxis } from 'recharts';

const statCards = [
  { title: 'Total Findings', value: '1,247', accent: 'text-white', trend: '+12.4%' },
  { title: 'Critical Risk Count', value: '42', accent: 'text-red-400', trend: 'High priority' },
  { title: 'Scans This Month', value: '18', accent: 'text-white', trend: '+3 new' },
  { title: 'Compliance Score', value: '87%', accent: 'text-emerald-400', trend: 'On track' },
];

const donutData = [
  { name: 'Critical', value: 42, color: '#ef4444' },
  { name: 'High', value: 109, color: '#f59e0b' },
  { name: 'Medium', value: 218, color: '#3b82f6' },
  { name: 'Low', value: 878, color: '#10b981' },
];

const trendData = [
  { day: 'Mon', findings: 38, critical: 12 },
  { day: 'Tue', findings: 46, critical: 15 },
  { day: 'Wed', findings: 52, critical: 18 },
  { day: 'Thu', findings: 40, critical: 14 },
  { day: 'Fri', findings: 64, critical: 22 },
  { day: 'Sat', findings: 49, critical: 19 },
  { day: 'Sun', findings: 58, critical: 25 },
];

const findings = [
  { severity: 'CRITICAL', file: 'src/auth/legacy_login.py:42', algorithm: 'MD5', line: 42, confidence: 'Verified', risk: 'Critical', date: '2026-08-24' },
  { severity: 'HIGH', file: 'src/utils/cert_gen.py:15', algorithm: 'RSA', line: 15, confidence: 'Probable', risk: 'High', date: '2026-08-23' },
  { severity: 'MEDIUM', file: 'src/api/handlers.js:88', algorithm: 'SHA-1', line: 88, confidence: 'Unverified', risk: 'Medium', date: '2026-08-21' },
  { severity: 'LOW', file: 'lib/encryption.c:112', algorithm: 'AES', line: 112, confidence: 'Verified', risk: 'Low', date: '2026-08-20' },
];

const sideItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Scan History', icon: Activity },
  { label: 'Reports', icon: FileText },
  { label: 'CBOM Library', icon: FolderOpen },
  { label: 'Settings', icon: Settings },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('Overview');

  const total = useMemo(() => donutData.reduce((sum, item) => sum + item.value, 0), []);

  return (
    <div className="min-h-screen bg-primary text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-primary/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-blue/20 text-accent-blue">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">ECDAT</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Dashboard</div>
            </div>
          </div>

          <div className="hidden items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-300 md:flex">
            <Search className="h-4 w-4 text-slate-500" />
            <span>Search scans, findings, repos...</span>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative rounded-full border border-slate-700 p-2 text-slate-200">
              <Bell className="h-4 w-4" />
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-red-500" />
            </button>
            <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-2 py-1.5">
              <UserCircle className="h-7 w-7 text-slate-300" />
              <div className="hidden text-left sm:block">
                <div className="text-sm font-medium text-white">Analyst</div>
                <div className="text-[10px] text-slate-400">analyst@ecdat.local</div>
              </div>
              <ChevronDown className="h-4 w-4 text-slate-400" />
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1600px]">
        <aside className="hidden min-h-[calc(100vh-64px)] w-56 border-r border-slate-800 bg-slate-950/70 p-4 lg:block">
          <div className="space-y-2">
            {sideItems.map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => setActiveTab(label)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm ${activeTab === label ? 'border-l-2 border-accent-blue bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/80'}`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>

          <button className="mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-accent-blue px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-blue-400">
            <Plus className="h-4 w-4" />
            New Scan
          </button>
        </aside>

        <main className="flex-1 p-4 sm:p-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {statCards.map((card) => (
              <div key={card.title} className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
                  <span>{card.title}</span>
                  <ShieldCheck className="h-4 w-4 text-accent-blue" />
                </div>
                <div className={`mt-4 text-3xl font-black ${card.accent}`}>{card.value}</div>
                <div className="mt-2 text-xs text-slate-400">{card.trend}</div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
            <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="text-lg font-semibold text-white">Risk distribution</div>
                <button className="flex items-center gap-2 rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-300">Last 30 days <ChevronDown className="h-3 w-3" /></button>
              </div>
              <div className="h-64">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={donutData} dataKey="value" innerRadius={56} outerRadius={88} paddingAngle={2}>
                      {donutData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 text-center text-xl font-bold text-white">{total}</div>
              <div className="mt-2 text-center text-xs text-slate-400">findings</div>
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="text-lg font-semibold text-white">Finding trends</div>
                <div className="flex gap-2 text-xs">
                  {[ '7d', '30d', 'All' ].map((filter) => (
                    <button key={filter} className={`rounded-full px-2 py-1 ${filter === '30d' ? 'bg-accent-blue text-slate-950' : 'bg-slate-800 text-slate-300'}`}>{filter}</button>
                  ))}
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis dataKey="day" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Bar dataKey="findings" fill="#60a5fa" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-lg font-semibold text-white">Recent findings</div>
              <div className="flex items-center gap-3 text-sm text-slate-400">
                <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5"><ListFilter className="h-4 w-4" /> Filters</button>
                <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5"><Download className="h-4 w-4" /> Export</button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="pb-3">Severity</th>
                    <th className="pb-3">File</th>
                    <th className="pb-3">Algorithm</th>
                    <th className="pb-3">Line</th>
                    <th className="pb-3">Confidence</th>
                    <th className="pb-3">Risk Tier</th>
                    <th className="pb-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((item) => (
                    <tr key={item.file} className="border-t border-slate-800 text-slate-200">
                      <td className="py-3"><span className={`rounded-full border px-2 py-1 text-[11px] font-medium ${item.severity === 'CRITICAL' ? 'border-red-500/40 bg-red-500/10 text-red-300' : item.severity === 'HIGH' ? 'border-amber-500/40 bg-amber-500/10 text-amber-300' : item.severity === 'MEDIUM' ? 'border-blue-500/40 bg-blue-500/10 text-blue-300' : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'}`}>{item.severity}</span></td>
                      <td className="py-3 font-mono text-xs text-accent-blue">{item.file}</td>
                      <td className="py-3">{item.algorithm}</td>
                      <td className="py-3">{item.line}</td>
                      <td className="py-3">{item.confidence}</td>
                      <td className="py-3">{item.risk}</td>
                      <td className="py-3">{item.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
