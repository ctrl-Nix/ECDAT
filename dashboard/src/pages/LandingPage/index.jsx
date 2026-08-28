import { useEffect, useRef, useState } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import {
  ArrowRight, CheckCircle, CheckCircle2, Code2, FileSearch,
  ShieldCheck, Sparkles, Terminal, AlertTriangle, Zap, Lock,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

/* ── Data ──────────────────────────────────────────────────────────────── */
const trustStats = [
  { value: '73%',  label: 'Enterprises lack crypto inventory' },
  { value: '2026', label: 'NIST PQC deadline' },
  { value: '3+',   label: 'Languages scanned (AST)' },
  { value: '1.6',  label: 'CycloneDX spec version' },
];

const problems = [
  { title: 'Invisible Risk',     description: 'Cryptographic calls are buried deep in legacy code with no reliable inventory or mapping.' },
  { title: 'Quantum Deadline',   description: 'NIST\'s 2026 deadline leaves organizations little time to inventory and replace quantum-vulnerable algorithms.' },
  { title: 'Compliance Gap',     description: 'Manual audits cannot keep pace with NIST PQC and DPDP reporting obligations at enterprise scale.' },
];

const features = [
  { title: 'Multi-language AST scanner',   icon: Code2,       accent: 'cyan' },
  { title: 'Real-time audit dashboard',    icon: FileSearch,  accent: 'purple' },
  { title: 'AI-powered remediation',       icon: ShieldCheck, accent: 'cyan' },
  { title: 'CI/CD policy gating',          icon: CheckCircle2,accent: 'purple' },
  { title: 'CycloneDX 1.6 CBOM export',   icon: Terminal,    accent: 'cyan' },
  { title: 'Mosca urgency scoring',        icon: Zap,         accent: 'purple' },
];

const comparisonRows = [
  ['Inventory coverage',    'Partial',  'Limited',  '✅ Complete'],
  ['AST scanning',          '❌',       '❌',       '✅ Full'],
  ['CycloneDX export',      '❌',       '⚠️ Partial','✅ v1.6'],
  ['Quantum risk scoring',  '❌',       '⚠️ Basic', '✅ Mosca'],
  ['Policy gating (CI/CD)', '❌',       'Partial',  '✅ Built-in'],
  ['Self-hosted / air-gap', '❌',       '❌',       '✅ Yes'],
];

const scrollFeatures = [
  {
    id: "discovery",
    title: "Algorithmic Discovery",
    desc: "AST-based parsing maps every cryptographic primitive without regex false-positives.",
    code: "[INFO] Parsing AST for 847 files...\n[SCAN] Found MD5 in legacy_auth.py\n[SCAN] Found RSA-1024 in pki_core.c\n[WARN] Deprecated algorithms mapped."
  },
  {
    id: "scoring",
    title: "Mosca Urgency Scoring",
    desc: "Automatically calculate quantum vulnerability timelines against NIST migration deadlines.",
    code: "[EVAL] RSA-1024\n  ├─ Shor's Algo: Vulnerable\n  └─ NIST Deadline: 2026\n[RISK] Critical quantum exposure detected.\n[REMEDY] Upgrade to CRYSTALS-Kyber."
  },
  {
    id: "cbom",
    title: "CycloneDX 1.6 Exports",
    desc: "Generate continuous Cryptographic Bill of Materials (CBOM) for zero-trust compliance.",
    code: "{\n  \"bomFormat\": \"CycloneDX\",\n  \"specVersion\": \"1.6\",\n  \"components\": [\n    { \"type\": \"cryptographic-asset\", \"name\": \"MD5\" }\n  ]\n}"
  }
];

const ledgerFindings = [
  { id: 1, confidence: 'Verified',   algorithm: 'MD5',       source: 'auth_service/hash.py:42',          tier: 'CRITICAL', tierClass: 'badge-critical',  confidenceClass: 'text-green' },
  { id: 2, confidence: 'Probable',   algorithm: 'RSA-1024',  source: 'payment_gateway/crypto.java:112',  tier: 'CRITICAL', tierClass: 'badge-critical',  confidenceClass: 'text-medium', quantum: true },
  { id: 3, confidence: 'Verified',   algorithm: 'SHA-1',     source: 'legacy_api/digest.go:88',          tier: 'HIGH',     tierClass: 'badge-high',      confidenceClass: 'text-green' },
  { id: 4, confidence: 'Verified',   algorithm: 'AES-256-GCM',source: 'secure_vault/utils.js:18',       tier: 'LOW',      tierClass: 'badge-low',       confidenceClass: 'text-green' },
];

const fadeUp = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0 } };

/* ── Noise/Grid background ─────────────────────────────────────────────── */
function HeroBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="hero-ambient absolute left-1/2 top-1/2 h-[700px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full" />
      <div className="bg-grid absolute inset-0" />
      {/* Floating particles */}
      {Array.from({ length: 28 }).map((_, i) => {
        const x = (i * 37.3) % 100;
        const y = (i * 19.7) % 100;
        const size = i % 3 === 0 ? 2 : 1;
        const delay = (i * 0.31) % 4;
        return (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${x}%`, top: `${y}%`,
              width: size, height: size,
              background: i % 4 === 0 ? 'var(--purple)' : 'var(--cyan)',
              opacity: 0.25,
            }}
            animate={{ opacity: [0.1, 0.5, 0.1], scale: [1, 1.8, 1] }}
            transition={{ duration: 3.5 + delay * 0.4, delay, repeat: Infinity, ease: 'easeInOut' }}
          />
        );
      })}
    </div>
  );
}


/* ── Enterprise Scroll Reveal (Upgraded) ─────────────────────────────────── */
const Step0Terminal = () => (
  <div className="p-6 font-mono text-sm leading-relaxed space-y-4 h-full" style={{ background: '#0A1C0E' }}>
    <div className="flex gap-2">
      <span style={{ color: 'var(--t3)' }}>$</span>
      <span style={{ color: '#E4F0E5' }}>ecdat scan --deep --ast</span>
    </div>
    <div style={{ color: 'var(--t3)' }}>[SYSTEM] Initializing distributed AST parsers...</div>
    <div className="flex justify-between items-center border-b pb-3 mt-4" style={{ borderColor: 'var(--border)' }}>
      <span style={{ color: 'var(--t2)' }}>auth_service/legacy.py</span>
      <span className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest" style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>MD5 Detected</span>
    </div>
    <div className="flex justify-between items-center border-b pb-3" style={{ borderColor: 'var(--border)' }}>
      <span style={{ color: 'var(--t2)' }}>core_banking/pki.c</span>
      <span className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest" style={{ background: 'var(--critical)', color: '#fff' }}>RSA-1024</span>
    </div>
    <div className="flex justify-between items-center pt-2">
      <span style={{ color: 'var(--t2)' }}>data_warehouse/ingest.go</span>
      <span className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest" style={{ background: 'var(--high)', color: '#fff' }}>SHA-1</span>
    </div>
  </div>
);

const Step1Risk = () => (
  <div className="p-8 space-y-6 h-full flex flex-col justify-center" style={{ background: 'var(--surface)' }}>
    <div className="flex items-center justify-between mb-2">
      <div className="text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: 'var(--t3)' }}>Mosca Urgency Report</div>
      <div className="text-xs font-semibold" style={{ color: 'var(--t2)' }}>Target: NIST 2026</div>
    </div>
    
    <div className="rounded-2xl p-6 flex flex-col gap-5 border shadow-sm" style={{ background: 'var(--void)', borderColor: 'var(--border)' }}>
      <div className="flex justify-between items-end">
        <div>
          <div className="text-3xl font-black tracking-tight" style={{ color: 'var(--critical)' }}>CRITICAL</div>
          <div className="text-[10px] uppercase font-bold tracking-widest mt-1.5" style={{ color: 'var(--t3)' }}>Quantum Exposure</div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-black tracking-tight" style={{ color: 'var(--t1)' }}>14 mo</div>
          <div className="text-[10px] uppercase font-bold tracking-widest mt-1.5" style={{ color: 'var(--t3)' }}>Time-to-migrate</div>
        </div>
      </div>
      <div className="h-2.5 w-full rounded-full overflow-hidden flex" style={{ background: 'var(--surface-r)' }}>
        <div className="h-full" style={{ width: '85%', background: 'var(--critical)' }} />
      </div>
    </div>

    <div className="grid grid-cols-2 gap-4">
      <div className="rounded-xl p-5 border shadow-sm" style={{ borderColor: 'var(--cyan)', background: 'var(--cyan-10)' }}>
        <div className="text-[10px] font-bold tracking-wider uppercase mb-1.5" style={{ color: 'var(--cyan)' }}>Suggested Action</div>
        <div className="text-[13px] font-bold leading-snug" style={{ color: 'var(--t1)' }}>Migrate to Kyber</div>
      </div>
      <div className="rounded-xl p-5 border shadow-sm" style={{ borderColor: 'var(--border)', background: 'var(--void)' }}>
        <div className="text-[10px] font-bold tracking-wider uppercase mb-1.5" style={{ color: 'var(--t3)' }}>Impact Radius</div>
        <div className="text-[13px] font-bold leading-snug" style={{ color: 'var(--t1)' }}>42 Microservices</div>
      </div>
    </div>
  </div>
);

const Step2CBOM = () => (
  <div className="p-6 font-mono text-[13px] leading-relaxed overflow-hidden h-full flex flex-col" style={{ background: 'var(--void)' }}>
    <div className="flex justify-between border-b pb-4 mb-4" style={{ borderColor: 'var(--border)' }}>
      <span className="font-bold" style={{ color: 'var(--t1)' }}>ecdat-export.json</span>
      <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--t3)' }}>CycloneDX v1.6</span>
    </div>
    <pre className="overflow-auto flex-1 text-[13px]">
<span style={{ color: 'var(--t3)' }}>{'{'}</span>
  <span style={{ color: 'var(--cyan)' }}>"bomFormat"</span>: <span style={{ color: 'var(--green)' }}>"CycloneDX"</span>,
  <span style={{ color: 'var(--cyan)' }}>"specVersion"</span>: <span style={{ color: 'var(--green)' }}>"1.6"</span>,
  <span style={{ color: 'var(--cyan)' }}>"components"</span>: <span style={{ color: 'var(--t3)' }}>[</span>
    <span style={{ color: 'var(--t3)' }}>{'{'}</span>
      <span style={{ color: 'var(--cyan)' }}>"type"</span>: <span style={{ color: 'var(--green)' }}>"crypto-asset"</span>,
      <span style={{ color: 'var(--cyan)' }}>"name"</span>: <span style={{ color: 'var(--green)' }}>"RSA-1024"</span>,
      <span style={{ color: 'var(--cyan)' }}>"cryptoProperties"</span>: <span style={{ color: 'var(--t3)' }}>{'{'}</span>
        <span style={{ color: 'var(--cyan)' }}>"assetType"</span>: <span style={{ color: 'var(--green)' }}>"algorithm"</span>
      <span style={{ color: 'var(--t3)' }}>{'}'}</span>
    <span style={{ color: 'var(--t3)' }}>{'}'}</span>
  <span style={{ color: 'var(--t3)' }}>]</span>
<span style={{ color: 'var(--t3)' }}>{'}'}</span>
    </pre>
  </div>
);

function EnterpriseScrollFeatures() {
  const [activeIdx, setActiveIdx] = useState(0);

  const getRightContent = (idx) => {
    switch (idx) {
      case 0: return <Step0Terminal />;
      case 1: return <Step1Risk />;
      case 2: return <Step2CBOM />;
      default: return null;
    }
  };

  return (
    <section className="relative mx-auto max-w-7xl px-4 py-32 sm:px-6 lg:px-8 border-y" style={{ borderColor: 'var(--border)' }}>
      <div className="mb-24 text-center">
        <div className="text-[12px] font-bold uppercase tracking-[0.4em] mb-4" style={{ color: 'var(--cyan)' }}>Deep code visibility</div>
        <h2 className="text-4xl md:text-5xl font-black tracking-tight" style={{ color: 'var(--t1)' }}>Uncover what's hidden in plain sight.</h2>
      </div>
      
      <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-[1fr_1.2fr] lg:gap-20">
        {/* Left: Text blocks with Progress Line */}
        <div className="relative space-y-4 lg:py-[20vh] lg:pb-[30vh]">
          {/* Vertical progress rail */}
          <div className="absolute left-0 top-0 bottom-0 w-[3px] hidden lg:block rounded-full" style={{ background: 'var(--surface-r)' }}>
             <motion.div 
                className="w-full origin-top rounded-full"
                style={{ background: 'var(--cyan)' }}
                initial={{ scaleY: 0 }}
                animate={{ scaleY: (activeIdx + 0.5) / scrollFeatures.length }}
                transition={{ type: 'spring', stiffness: 60, damping: 15 }}
             />
          </div>

          {scrollFeatures.map((f, i) => (
            <motion.div 
              key={f.id}
              initial={{ opacity: 0.2 }}
              whileInView={{ opacity: 1 }}
              viewport={{ margin: "-50% 0px -50% 0px" }}
              onViewportEnter={() => setActiveIdx(i)}
              className="relative rounded-3xl p-8 transition-all duration-700 lg:min-h-[55vh] lg:border-transparent lg:bg-transparent lg:pl-16 lg:p-0"
              style={{ 
                opacity: activeIdx === i ? 1 : 0.25,
                transform: activeIdx === i ? 'translateX(12px)' : 'translateX(0px)'
              }}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl mb-8 shadow-sm transition-colors duration-500" style={{ background: activeIdx === i ? 'var(--cyan-10)' : 'var(--surface-r)', color: activeIdx === i ? 'var(--cyan)' : 'var(--t3)' }}>
                {i === 0 ? <FileSearch size={28} strokeWidth={2.5} /> : i === 1 ? <AlertTriangle size={28} strokeWidth={2.5} /> : <Code2 size={28} strokeWidth={2.5} />}
              </div>
              <h3 className="text-3xl font-black mb-5 tracking-tight transition-colors duration-500" style={{ color: activeIdx === i ? 'var(--t1)' : 'var(--t3)' }}>
                {f.title}
              </h3>
              <p className="text-lg leading-relaxed font-medium transition-colors duration-500" style={{ color: activeIdx === i ? 'var(--t2)' : 'var(--t4)' }}>
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Right: Sticky Terminal / Dash */}
        <div className="sticky top-40 overflow-hidden rounded-2xl border shadow-2xl transition-all duration-700" style={{ borderColor: 'var(--border)', background: 'var(--surface-r)', height: '480px' }}>
          {/* Mac-style traffic light header */}
          <div className="flex items-center gap-2 border-b px-5 py-4 backdrop-blur-xl" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
            <span className="h-3 w-3 rounded-full border" style={{ background: '#FF5F56', borderColor: '#E0443E' }} />
            <span className="h-3 w-3 rounded-full border" style={{ background: '#FFBD2E', borderColor: '#DEA123' }} />
            <span className="h-3 w-3 rounded-full border" style={{ background: '#27C93F', borderColor: '#1AAB29' }} />
            <span className="ml-5 text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: 'var(--t3)' }}>ecdat · live-view</span>
          </div>
          
          <div className="relative h-[calc(100%-53px)] w-full overflow-hidden">
            {scrollFeatures.map((f, i) => (
              <motion.div
                key={f.id}
                initial={{ opacity: 0, scale: 0.98, y: 15 }}
                animate={{ 
                  opacity: activeIdx === i ? 1 : 0, 
                  scale: activeIdx === i ? 1 : 0.98, 
                  y: activeIdx === i ? 0 : 15,
                  pointerEvents: activeIdx === i ? 'auto' : 'none' 
                }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="absolute inset-0 h-full w-full bg-[var(--surface-h)]"
              >
                {getRightContent(i)}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── Main ──────────────────────────────────────────────────────────────── */
export default function LandingPage() {
  const heroRef = useRef(null);
  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 500], [1, 0]);
  const heroY       = useTransform(scrollY, [0, 500], [0, -60]);

  useEffect(() => {
    // GSAP removed to prevent conflict with Framer Motion initial={{opacity:0}}
    // The section wrapper handles the scroll-fade via Framer Motion useScroll
  }, []);

  return (
    <div className="min-h-screen bg-void font-sans">

      {/* ── HERO ─────────────────────────────────────────────────────── */}
      <motion.section
        ref={heroRef}
        style={{ opacity: heroOpacity, y: heroY }}
        className="relative flex h-screen flex-col items-center justify-center overflow-hidden"
      >
        <HeroBackground />

        <div className="relative z-10 flex w-full max-w-6xl flex-col items-center px-4 text-center">

          {/* Nav pill */}
          <div className="mb-10 flex w-full max-w-3xl items-center justify-between rounded-full border px-5 py-3 backdrop-blur-md"
            style={{ borderColor: 'var(--border-s)', background: 'var(--surface)', opacity: 0.95 }}>
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
                <ShieldCheck className="h-4 w-4" />
              </div>
              <span className="text-base font-bold tracking-tight" style={{ color: 'var(--t1)' }}>ECDAT</span>
            </div>
            <nav className="hidden items-center gap-6 text-sm md:flex" style={{ color: 'var(--t2)' }}>
              {['Product', 'Ledger', 'Scanner', 'Compliance'].map((l) => (
                <a key={l} href={`#${l.toLowerCase()}`}
                  className="hover:text-t1 transition-colors" style={{ color: 'var(--t2)' }} onMouseOver={e=>e.currentTarget.style.color='var(--t1)'} onMouseOut={e=>e.currentTarget.style.color='var(--t2)'}>{l}</a>
              ))}
            </nav>
            <div className="flex items-center gap-2">
              <Link to="/login" className="hidden rounded-full border px-4 py-1.5 text-sm font-medium sm:inline-flex transition-colors"
                style={{ borderColor: 'var(--border-s)', color: 'var(--t2)' }} onMouseOver={e=>e.currentTarget.style.color='var(--t1)'} onMouseOut={e=>e.currentTarget.style.color='var(--t2)'}>Log in</Link>
              <Link to="/login" className="btn-primary rounded-full px-4 py-1.5">Get started</Link>
            </div>
          </div>

          {/* Status badge */}
          <motion.div
            className="gsap-hero-badge inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium backdrop-blur mb-7"
            style={{ borderColor: 'rgba(0,200,255,0.2)', background: 'var(--cyan-10)', color: 'var(--cyan)' }}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          >
            <span className="live-ping relative flex h-1.5 w-1.5 rounded-full" style={{ background: 'var(--cyan)' }} />
            NIST PQC-aligned · CycloneDX 1.6 · Self-hosted · Zero egress
          </motion.div>

          {/* Headline */}
          <motion.h1
            className="gsap-hero-h1 mx-auto max-w-5xl text-5xl font-black tracking-tight sm:text-6xl lg:text-[82px] leading-[1.03]"
            style={{ color: 'var(--t1)' }}
            initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.55 }}
          >
            Know your cryptography.{' '}
            <span className="relative inline-block"
              style={{ backgroundImage: 'linear-gradient(135deg, var(--cyan) 0%, var(--purple) 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Before quantum does.
            </span>
          </motion.h1>

          {/* Sub */}
          <motion.p
            className="gsap-hero-sub mx-auto mt-6 max-w-2xl text-lg leading-relaxed"
            style={{ color: 'var(--t2)' }}
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
          >
            AST-powered cryptographic discovery across your entire codebase.
            Map every algorithm, score quantum risk with Mosca's theorem, and generate
            a CycloneDX CBOM — before compliance pressure hits.
          </motion.p>

          {/* CTAs */}
          <motion.div className="mt-8 flex flex-col items-center gap-4 sm:flex-row"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.65 }}>
            <Link to="/login" className="btn-primary flex items-center gap-2 rounded-full px-7 py-3.5 text-sm">
              Start scanning <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#ledger" className="btn-ghost flex items-center gap-2 rounded-full px-7 py-3.5 text-sm">
              View audit ledger
            </a>
          </motion.div>

          {/* Trust */}
          <motion.div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-sm"
            style={{ color: 'var(--t3)' }}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
            {['No false positive noise', 'AST-led · not regex', 'Air-gap deployable'].map((t) => (
              <span key={t} className="inline-flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5" style={{ color: 'var(--green)' }} /> {t}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Scroll cue */}
        <motion.div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
          animate={{ y: [0, 8, 0] }} transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}>
          <div className="h-10 w-5 rounded-full border flex items-start justify-center pt-1.5"
            style={{ borderColor: 'var(--border-s)' }}>
            <div className="h-2 w-0.5 rounded-full" style={{ background: 'var(--cyan)' }} />
          </div>
        </motion.div>
      </motion.section>

      {/* ── ENTERPRISE SCROLL REVEAL ─────────────────────────────────── */}
      <EnterpriseScrollFeatures />

      {/* ── TRUST STATS ──────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}
          variants={fadeUp} transition={{ duration: 0.45 }}
          className="grid gap-px rounded-[14px] border overflow-hidden sm:grid-cols-2 lg:grid-cols-4"
          style={{ borderColor: 'var(--border)', background: 'var(--border)' }}
        >
          {trustStats.map((stat, i) => (
            <div key={stat.label} className="p-8 text-center" style={{ background: 'var(--surface)' }}>
              <div className="text-4xl font-black num" style={{
                backgroundImage: 'linear-gradient(135deg, var(--cyan), var(--purple))',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>{stat.value}</div>
              <div className="mt-2 text-sm" style={{ color: 'var(--t2)' }}>{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── LIVE AUDIT LEDGER ────────────────────────────────────────── */}
      <section id="ledger" className="relative z-10 mx-auto max-w-6xl px-4 py-24 sm:px-6 lg:px-8">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.15 }}
          variants={fadeUp} transition={{ duration: 0.45 }}>

          <div className="mb-10 flex items-end justify-between">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-[0.3em] mb-3" style={{ color: 'var(--cyan)' }}>
                Live Audit Ledger
              </div>
              <h2 className="text-3xl font-bold" style={{ color: 'var(--t1)' }}>Real-time finding stream</h2>
              <p className="mt-2 text-sm" style={{ color: 'var(--t2)' }}>
                Every cryptographic artifact — discovered, classified, and scored.
              </p>
            </div>
            <Link to="/login" className="btn-primary hidden sm:inline-flex rounded-xl px-5 py-2.5">
              Export CBOM
            </Link>
          </div>

          {/* Live pulse header */}
          <div className="flex items-center gap-2 mb-3 text-xs" style={{ color: 'var(--t3)' }}>
            <span className="live-ping relative flex h-1.5 w-1.5 rounded-full" style={{ background: 'var(--green)' }} />
            Live stream — syncing every 30s
          </div>

          <div className="card overflow-hidden" style={{ background: 'var(--surface)', backdropFilter: 'blur(12px)', opacity: 0.95 }}>
            {/* Table header */}
            <div className="grid grid-cols-[1fr_1fr_2fr_1fr_100px] border-b px-5 py-3"
              style={{ borderColor: 'var(--border)', color: 'var(--t3)', fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase' }}>
              <div>Confidence</div><div>Algorithm</div><div>Source origin</div><div>Risk tier</div><div className="text-right">Action</div>
            </div>

            {ledgerFindings.map((f, i) => (
              <motion.div
                key={f.id}
                initial={{ opacity: 0, x: -12 }} whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="grid grid-cols-[1fr_1fr_2fr_1fr_100px] items-center border-b px-5 py-4 transition-colors"
                style={{ borderColor: 'rgba(22,33,58,0.5)' }}
                onMouseOver={e=>e.currentTarget.style.background='rgba(255,255,255,0.015)'}
                onMouseOut={e=>e.currentTarget.style.background='transparent'}
              >
                <div className="flex items-center gap-2 text-sm" style={{ color: f.confidenceClass.includes('green') ? 'var(--green)' : 'var(--medium)' }}>
                  <CheckCircle className="h-3.5 w-3.5" />{f.confidence}
                </div>
                <div className="mono font-semibold text-sm flex items-center gap-2"
                  style={{ color: f.tier === 'LOW' ? 'var(--green)' : f.tier === 'CRITICAL' ? 'var(--critical)' : 'var(--high)' }}>
                  {f.algorithm}
                  {f.quantum && <Zap className="h-3 w-3" style={{ color: 'var(--purple)' }} />}
                </div>
                <div className="mono text-xs truncate" style={{ color: 'var(--t2)' }}>{f.source}</div>
                <div>
                  <span className={`badge ${f.tierClass}`}>
                    {f.tier}
                  </span>
                </div>
                <div className="text-right">
                  <Link to="/login" className="text-xs font-medium transition-colors"
                    style={{ color: 'var(--cyan)' }} onMouseOver={e=>e.currentTarget.style.opacity=0.8} onMouseOut={e=>e.currentTarget.style.opacity=1}>Remediate →</Link>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── PROBLEM ──────────────────────────────────────────────────── */}
      <section id="product" className="relative z-10 mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
          variants={fadeUp} transition={{ duration: 0.45 }}>
          <div className="mb-10 text-center">
            <div className="text-[11px] font-bold uppercase tracking-[0.3em] mb-3" style={{ color: 'var(--cyan)' }}>The problem</div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--t1)' }}>You can't migrate what you can't find.</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {problems.map((item, i) => (
              <motion.div key={item.title}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                className="card p-6 transition-colors"
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--cyan)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--t1)' }}>{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--t2)' }}>{item.description}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── COMPARISON ───────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
          variants={fadeUp} transition={{ duration: 0.45 }}
          className="card p-8" style={{ background: 'var(--surface)', opacity: 0.95 }}>
          <div className="mb-8 text-center">
            <div className="text-[11px] font-bold uppercase tracking-[0.3em] mb-3" style={{ color: 'var(--cyan)' }}>Why ECDAT?</div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--t1)' }}>Built for enterprise. Not SaaS.</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  {['Feature', 'Regex scanners', 'SaaS tools', 'ECDAT'].map((h, i) => (
                    <th key={h} className="pb-4 pr-8 text-left text-xs font-bold uppercase tracking-wider"
                      style={{ color: i === 3 ? 'var(--cyan)' : 'var(--t3)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map(([feature, regex, saas, ecdat]) => (
                  <tr key={feature} className="border-b" style={{ borderColor: 'rgba(22,33,58,0.5)' }}>
                    <td className="py-3 pr-8 font-medium" style={{ color: 'var(--t1)' }}>{feature}</td>
                    <td className="py-3 pr-8" style={{ color: 'var(--t3)' }}>{regex}</td>
                    <td className="py-3 pr-8" style={{ color: 'var(--t3)' }}>{saas}</td>
                    <td className="py-3 pr-8 font-semibold" style={{ color: 'var(--green)' }}>{ecdat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────── */}
      <section id="compliance" className="relative z-10 mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.15 }}
          variants={fadeUp} transition={{ duration: 0.45 }}>
          <div className="mb-10 text-center">
            <div className="text-[11px] font-bold uppercase tracking-[0.3em] mb-3" style={{ color: 'var(--cyan)' }}>Capabilities</div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--t1)' }}>Enterprise-grade cryptographic assessment.</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {features.map(({ title, icon: Icon, accent }, i) => (
              <motion.div key={title}
                initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.07 }}
                className="card p-6 transition-colors"
                onMouseEnter={(e) => e.currentTarget.style.borderColor = accent === 'cyan' ? 'var(--cyan)' : 'var(--purple)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: accent === 'cyan' ? 'var(--cyan-10)' : 'var(--purple-10)', color: accent === 'cyan' ? 'var(--cyan)' : 'var(--purple)' }}>
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold" style={{ color: 'var(--t1)' }}>{title}</h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--t2)' }}>
                  High-confidence discovery and risk reporting for every cryptographic artifact in your codebase.
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── SCANNER DEMO ─────────────────────────────────────────────── */}
      <section id="scanner" className="relative z-10 mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.15 }}
          variants={fadeUp} transition={{ duration: 0.45 }}
          className="card p-8" style={{ background: 'var(--surface)', opacity: 0.95 }}>
          <div className="grid gap-10 lg:grid-cols-[1fr_1.3fr] lg:items-center">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-[0.3em] mb-3" style={{ color: 'var(--cyan)' }}>See it in action</div>
              <h2 className="text-3xl font-bold" style={{ color: 'var(--t1)' }}>Scan in seconds. Know in minutes.</h2>
              <ul className="mt-6 space-y-4">
                {[
                  'AST analysis maps crypto usage across Python, Go, Java, JS, Rust, C.',
                  'Mosca urgency scoring prioritizes quantum-vulnerable findings first.',
                  'CycloneDX 1.6 CBOM exported to integrate with any compliance pipeline.',
                ].map((li) => (
                  <li key={li} className="flex items-start gap-3 text-sm" style={{ color: 'var(--t2)' }}>
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--green)' }} /> {li}
                  </li>
                ))}
              </ul>
              <Link to="/login" className="btn-primary mt-8 inline-flex items-center gap-2 rounded-full px-6 py-3">
                Explore dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {/* Terminal */}
            <div className="terminal">
              <div className="terminal-bar">
                <span className="terminal-dot" style={{ background: '#ff3d3d' }} />
                <span className="terminal-dot" style={{ background: '#fbbf24' }} />
                <span className="terminal-dot" style={{ background: '#00e5a0' }} />
                <span className="ml-4 text-xs font-mono" style={{ color: 'var(--t3)' }}>ecdat-scan — zsh</span>
              </div>
              <pre className="overflow-x-auto p-5 font-mono text-sm leading-7">
                <span style={{ color: 'var(--t3)' }}>$ </span>
                <span style={{ color: 'var(--cyan)' }}>ecdat</span>
                <span style={{ color: 'var(--t1)' }}>{' scan github.com/enterprise/core-banking\n'}</span>
                <span style={{ color: 'var(--t3)' }}>[INFO] Cloning repository... done\n</span>
                <span style={{ color: 'var(--t3)' }}>[INFO] Indexing 847 source files...\n</span>
                <span style={{ color: 'var(--high)' }}>[WARN] MD5 → src/auth/legacy_login.py:42\n</span>
                <span style={{ color: 'var(--critical)' }}>[CRIT] RSA-1024 → src/utils/cert_gen.py:15\n</span>
                <span style={{ color: 'var(--green)' }}>[PASS] AES-256-GCM → lib/secure_store.py:77\n</span>
                <span style={{ color: 'var(--cyan)' }}>[CBOM] Generated CycloneDX 1.6 (12 assets)\n</span>
                <span style={{ color: 'var(--high)' }}>[DONE] 3 high-priority findings flagged</span>
                <span className="cursor" />
              </pre>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────── */}
      <footer id="docs" className="border-t" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 text-sm sm:px-6 lg:grid-cols-4 lg:px-8" style={{ color: 'var(--t2)' }}>
          <div>
            <div className="flex items-center gap-3 mb-4" style={{ color: 'var(--t1)' }}>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg" style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
                <ShieldCheck className="h-4 w-4" />
              </div>
              <span className="font-semibold">ECDAT</span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--t3)' }}>
              Enterprise Cryptographic Discovery & Analysis Tool
            </p>
          </div>
          {[
            {
              title: 'Platform',
              links: [
                { label: 'Scanner', href: '#scanner' },
                { label: 'Dashboard', href: '/dashboard' },
                { label: 'Compliance', href: '#compliance' },
                { label: 'CBOM', href: '#features' },
              ],
            },
            {
              title: 'Resources',
              links: [
                { label: 'Docs', href: '#docs' },
                { label: 'API Reference', href: 'http://127.0.0.1:8000/docs', external: true },
                { label: 'Support', href: '#docs' },
              ],
            },
            {
              title: 'Team',
              links: [
                { label: 'Port 53', href: 'https://sih.gov.in/', external: true },
                { label: 'SIH 2026', href: 'https://sih.gov.in/', external: true },
                { label: 'PS 26164', href: 'https://sih.gov.in/sih2026PS', external: true },
              ],
            },
          ].map(({ title, links }) => (
            <div key={title}>
              <div className="mb-4 font-semibold text-xs uppercase tracking-wider" style={{ color: 'var(--t1)' }}>{title}</div>
              <ul className="space-y-2">
                {links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      target={l.external ? "_blank" : undefined}
                      rel={l.external ? "noopener noreferrer" : undefined}
                      className="text-xs transition-colors block"
                      style={{ color: 'var(--t3)', textDecoration: 'none' }}
                      onMouseOver={(e) => (e.currentTarget.style.color = 'var(--t1)')}
                      onMouseOut={(e) => (e.currentTarget.style.color = 'var(--t3)')}
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t py-4 text-center text-xs" style={{ borderColor: 'var(--border)', color: 'var(--t4)' }}>
          © 2026 Team Port 53 · <a href="https://sih.gov.in/" target="_blank" rel="noopener noreferrer" className="transition-colors hover:underline" style={{ color: 'var(--t3)' }}>Smart India Hackathon</a> · <a href="https://sih.gov.in/sih2026PS" target="_blank" rel="noopener noreferrer" className="transition-colors hover:underline" style={{ color: 'var(--t3)' }}>PS 26164</a>
        </div>
      </footer>
    </div>
  );
}
