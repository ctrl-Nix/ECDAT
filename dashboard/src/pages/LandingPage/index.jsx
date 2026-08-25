import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, Code2, FileSearch, ShieldCheck, Sparkles, Terminal } from 'lucide-react';
import { Link } from 'react-router-dom';

const trustStats = [
  { value: '73%', label: 'Enterprises lack inventory' },
  { value: '2026', label: 'NIST deadline' },
  { value: '3', label: 'Languages' },
  { value: '1.6', label: 'CycloneDX version' },
];

const problems = [
  { title: 'Invisible Risk', description: 'Cryptographic calls are buried deep in legacy code with no reliable inventory.' },
  { title: 'Quantum Deadline', description: 'The 2026 deadline leaves little time to inventory and replace vulnerable algorithms.' },
  { title: 'Compliance Gap', description: 'Manual audits cannot keep up with NIST and DPDP reporting obligations.' },
];

const features = [
  { title: 'Multi-language scanner', icon: Code2 },
  { title: 'Real-time dashboard', icon: FileSearch },
  { title: 'Automated remediation', icon: ShieldCheck },
  { title: 'CI/CD gating', icon: CheckCircle2 },
  { title: 'CBOM export', icon: Terminal },
  { title: 'Compliance reporting', icon: ShieldCheck },
];

const comparisonRows = [
  ['Inventory coverage', 'Partial', 'Limited', 'Complete'],
  ['AST scanning', '❌', '❌', '✅'],
  ['CycloneDX export', '❌', '⚠️', '✅'],
  ['Quantum risk scoring', '❌', '⚠️', '✅'],
  ['Policy controls', '❌', 'Partial', '✅'],
  ['Self-hosted', '❌', '❌', '✅'],
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-primary text-slate-100">
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <motion.section
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ duration: 0.5 }}
          className="rounded-[32px] border border-slate-700 bg-slate-950/60 p-6 shadow-glow"
        >
          <div className="flex items-center justify-between gap-4 rounded-full border border-slate-700 bg-slate-900/70 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-blue/20 text-accent-blue">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <span className="text-xl font-semibold tracking-tight">ECDAT</span>
            </div>

            <nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
              <a href="#product" className="hover:text-white">Product</a>
              <a href="#scanner" className="hover:text-white">Scanner</a>
              <a href="#compliance" className="hover:text-white">Compliance</a>
              <a href="#docs" className="hover:text-white">Docs</a>
            </nav>

            <div className="flex items-center gap-3">
              <Link to="/login" className="hidden rounded-full border border-slate-600 px-4 py-2 text-sm font-medium hover:border-slate-500 sm:inline-flex">Log in</Link>
              <Link to="/login" className="rounded-full bg-accent-blue px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-blue-400">Get started</Link>
            </div>
          </div>

          <div className="mt-16 text-center">
            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-medium text-slate-200">
              <Sparkles className="h-4 w-4 text-accent-blue" />
              NIST-Aligned • CycloneDX 1.6 • Self-Hosted
            </div>

            <h1 className="mx-auto mt-8 max-w-4xl text-4xl font-black tracking-tight text-white sm:text-5xl lg:text-7xl">
              Know Your Cryptography. <span className="text-accent-blue">Before Quantum Does.</span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
              Discover weak cryptographic usage, map each asset, and generate a CycloneDX CBOM before compliance pressure arrives.
            </p>

            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link to="/login" className="inline-flex items-center gap-2 rounded-full bg-accent-blue px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-blue-400">
                Start scanning
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#scanner" className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-6 py-3 text-sm font-semibold text-white hover:border-slate-500">
                View demo
              </a>
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-300">
              <span className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Minimum false positives</span>
              <span className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> AST-led scanning</span>
              <span className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> CBOM ready</span>
            </div>
          </div>
        </motion.section>

        <section className="mt-10 grid gap-4 rounded-2xl border border-slate-700 bg-slate-900/60 p-4 sm:grid-cols-2 lg:grid-cols-4">
          {trustStats.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-slate-700 bg-slate-800/80 p-6 text-center">
              <div className="text-3xl font-black text-white">{stat.value}</div>
              <div className="mt-2 text-sm text-slate-400">{stat.label}</div>
            </div>
          ))}
        </section>

        <motion.section id="product" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }} variants={fadeUp} transition={{ duration: 0.45 }} className="mt-20">
          <div className="mb-8 text-center">
            <div className="text-xs font-bold uppercase tracking-[0.25em] text-accent-blue">The problem</div>
            <h2 className="mt-3 text-3xl font-bold text-white">You can't migrate what you can't find.</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {problems.map((item) => (
              <div key={item.title} className="rounded-2xl border border-slate-700 bg-slate-900/80 p-6 hover:border-slate-500">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent-blue/15 text-accent-blue">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-semibold text-white">{item.title}</h3>
                <p className="mt-3 text-slate-300">{item.description}</p>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }} variants={fadeUp} transition={{ duration: 0.45 }} className="mt-20 rounded-2xl border border-slate-700 bg-slate-900/60 p-6">
          <div className="mb-6 text-center">
            <div className="text-xs font-bold uppercase tracking-[0.25em] text-accent-blue">Why ECDAT?</div>
            <h2 className="mt-3 text-3xl font-bold text-white">Built for enterprise. Not for SaaS.</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-200">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="pb-4 pr-4">Feature</th>
                  <th className="pb-4 pr-4">Regex scanners</th>
                  <th className="pb-4 pr-4">SaaS tools</th>
                  <th className="pb-4 pr-4 text-accent-blue">ECDAT</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map(([feature, regex, saas, ecdat]) => (
                  <tr key={feature} className="border-b border-slate-800">
                    <td className="py-3 pr-4 font-medium text-white">{feature}</td>
                    <td className="py-3 pr-4 text-slate-300">{regex}</td>
                    <td className="py-3 pr-4 text-slate-300">{saas}</td>
                    <td className="py-3 pr-4 font-semibold text-accent-blue">{ecdat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>

        <motion.section initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }} variants={fadeUp} transition={{ duration: 0.45 }} className="mt-20">
          <div className="mb-8 text-center">
            <div className="text-xs font-bold uppercase tracking-[0.25em] text-accent-blue">Features</div>
            <h2 className="mt-3 text-3xl font-bold text-white">Everything you need for cryptographic assessment.</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {features.map(({ title, icon: Icon }) => (
              <div key={title} className="rounded-2xl border border-slate-700 bg-slate-900/80 p-6 hover:border-slate-500">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-accent-blue/15 text-accent-blue">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-semibold text-white">{title}</h3>
                <p className="mt-3 text-slate-300">High-confidence discovery and risk reporting for every cryptographic artifact in the codebase.</p>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section id="scanner" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }} variants={fadeUp} transition={{ duration: 0.45 }} className="mt-20 rounded-2xl border border-slate-700 bg-slate-900/80 p-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr] lg:items-center">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.25em] text-accent-blue">See it in action</div>
              <h2 className="mt-3 text-3xl font-bold text-white">Scan your codebase in seconds.</h2>
              <ul className="mt-6 space-y-4 text-slate-300">
                <li className="flex items-center gap-3"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> AST analysis maps crypto usage across multiple languages.</li>
                <li className="flex items-center gap-3"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Report prioritizes quantum-risk impact and remediation plans.</li>
                <li className="flex items-center gap-3"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Export standards-compliant CycloneDX assets to compliance workflows.</li>
              </ul>
              <Link to="/login" className="mt-8 inline-flex items-center gap-2 rounded-full bg-accent-blue px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-blue-400">Explore the dashboard</Link>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950">
              <div className="flex items-center gap-2 border-b border-slate-700 px-4 py-3">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                <span className="h-3 w-3 rounded-full bg-amber-400" />
                <span className="h-3 w-3 rounded-full bg-emerald-500" />
                <span className="ml-4 text-xs text-slate-400">ecdat-scan</span>
              </div>
              <pre className="overflow-x-auto p-4 font-mono text-sm leading-6 text-slate-200">
{`ecdat scan github.com/enterprise/core-banking
[INFO] Discovering cryptographic assets...
[WARN] MD5 found in src/auth/legacy_login.py:42
[WARN] RSA-1024 detected in src/utils/cert_gen.py:15
[PASS] AES-256-GCM verified in lib/secure_store.py:77
[REPORT] Generated CycloneDX 1.6 CBOM (12 assets)
[STATUS] 3 high-priority findings flagged`}
              </pre>
            </div>
          </div>
        </motion.section>
      </main>

      <footer id="docs" className="border-t border-slate-700 bg-slate-950/80">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm text-slate-400 sm:px-6 lg:grid-cols-4 lg:px-8">
          <div>
            <div className="flex items-center gap-3 text-white">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-blue/20 text-accent-blue">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <span className="font-semibold">ECDAT</span>
            </div>
            <p className="mt-4">Enterprise Cryptographic Discovery & Analysis Tool</p>
          </div>
          <div>
            <div className="font-semibold text-white">Platform</div>
            <ul className="mt-4 space-y-2">
              <li>Scanner</li>
              <li>Dashboard</li>
              <li>Compliance</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-white">Resources</div>
            <ul className="mt-4 space-y-2">
              <li>Docs</li>
              <li>API</li>
              <li>Support</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-white">Team</div>
            <ul className="mt-4 space-y-2">
              <li>Port 53</li>
              <li>SIH 2026</li>
              <li>PS 26164</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-800 py-4 text-center text-xs text-slate-500">© 2026 Team Port 53. Built for Smart India Hackathon.</div>
      </footer>
    </div>
  );
}
