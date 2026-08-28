import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Play } from 'lucide-react';

// ==========================================
// SCENE 0: The Problem (Cryptographic Sprawl) - PERFECTLY ALIGNED GRID
// ==========================================
const Scene0 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 1500); 
    const t2 = setTimeout(() => setBeat(2), 2500); 
    const t3 = setTimeout(() => setBeat(3), 4500); 
    const t4 = setTimeout(() => setBeat(4), 5500); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, []);

  // X/Y coordinates precisely balanced to form a centered 5x2 grid
  const nodes = [
    { id: 1, label: 'RSA-1024', vuln: true,  rand: {x: -250, y: -120}, grid: {x: -320, y: -60} },
    { id: 2, label: 'AES-256',  vuln: false, rand: {x: 200, y: -100},  grid: {x: -160, y: -60} },
    { id: 3, label: 'MD5',      vuln: true,  rand: {x: -80, y: 120},   grid: {x: 0, y: -60} },
    { id: 4, label: 'SHA-256',  vuln: false, rand: {x: 150, y: -140},  grid: {x: 160, y: -60} },
    { id: 5, label: 'ECC-160',  vuln: true,  rand: {x: 280, y: 90},    grid: {x: 320, y: -60} },
    { id: 6, label: 'TLS 1.1',  vuln: true,  rand: {x: -200, y: 60},   grid: {x: -320, y: 60} },
    { id: 7, label: 'ChaCha20', vuln: false, rand: {x: 50, y: 140},    grid: {x: -160, y: 60} },
    { id: 8, label: 'SHA-1',    vuln: true,  rand: {x: 180, y: 40},    grid: {x: 0, y: 60} },
    { id: 9, label: 'HMAC',     vuln: false, rand: {x: -120, y: -80},  grid: {x: 160, y: 60} },
    { id: 10, label: 'DES',     vuln: true,  rand: {x: -50, y: -140},  grid: {x: 320, y: 60} },
  ];

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <motion.div 
        className="absolute inset-0 opacity-20"
        style={{ backgroundImage: 'linear-gradient(#1e293b 2px, transparent 2px), linear-gradient(90deg, #1e293b 2px, transparent 2px)', backgroundSize: '60px 60px' }}
        animate={{ backgroundPosition: ["0px 0px", "60px 60px"] }}
        transition={{ duration: 4, ease: "linear", repeat: Infinity }}
      />
      <div className="relative w-full h-full max-w-4xl max-h-[500px] flex items-center justify-center">
        <AnimatePresence>
          {beat >= 1 && beat < 3 && (
            <motion.div initial={{ scale: 0, opacity: 0.8 }} animate={{ scale: 15, opacity: 0 }} transition={{ duration: 2, ease: "easeOut" }}
              className="absolute w-20 h-20 bg-red-500/30 rounded-full border border-red-500" />
          )}
        </AnimatePresence>

        {nodes.map((node) => {
          const isRevealed = beat >= 2 && node.vuln;
          return (
            <motion.div key={node.id} 
              initial={{ x: node.rand.x, y: node.rand.y, opacity: 0 }}
              animate={{ 
                x: beat >= 3 ? node.grid.x : node.rand.x, 
                y: beat >= 3 ? node.grid.y : node.rand.y, 
                opacity: 1, 
                backgroundColor: isRevealed ? '#450a0a' : '#0f172a', 
                borderColor: isRevealed ? '#ef4444' : '#334155',
                scale: beat >= 4 && node.vuln ? [1, 1.05, 1] : 1
              }}
              transition={{ x: { type: "spring", stiffness: 60, damping: 14 }, y: { type: "spring", stiffness: 60, damping: 14 }, opacity: { duration: 0.5 }, scale: { repeat: Infinity, duration: 2, ease: "easeInOut" }, backgroundColor: { duration: 0.3 } }}
              className="absolute w-[120px] h-[50px] border-2 rounded-xl flex items-center justify-center shadow-2xl"
            >
              <motion.span animate={{ opacity: beat >= 2 ? 1 : 0 }} className={`font-mono text-sm font-bold ${node.vuln ? 'text-red-400' : 'text-slate-500'}`}>{node.label}</motion.span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};


// ==========================================
// SCENE 1: AST Scan
// ==========================================
const Scene1 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 1000); 
    const t2 = setTimeout(() => setBeat(2), 2000); 
    const t3 = setTimeout(() => setBeat(3), 3500); 
    const t4 = setTimeout(() => setBeat(4), 4500); 
    const t5 = setTimeout(() => setBeat(5), 6500); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); clearTimeout(t5); };
  }, []);

  const drawLine = { hidden: { pathLength: 0, opacity: 0 }, visible: { pathLength: 1, opacity: 1, transition: { duration: 1.5, ease: "easeInOut" } } };

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-[800px] h-[500px] flex items-center justify-center">
        <AnimatePresence>
          {beat >= 1 && beat < 3 && (
            <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="absolute top-[200px] w-[500px] h-[70px] bg-[#0f172a] border border-slate-700 rounded-xl shadow-2xl flex items-center px-6 overflow-hidden">
              <div className="font-mono text-lg text-slate-300 relative z-10 w-full">
                <span className="text-pink-400">const</span> hash = <span className="text-blue-400">crypto.createHash</span>(
                <span className={beat >= 2 ? "text-amber-400 font-bold transition-all" : "text-amber-400/50"}>'md5'</span>);
              </div>
              {beat >= 2 && (
                <motion.div initial={{ left: 0 }} animate={{ left: "100%" }} transition={{ duration: 1.2, ease: "linear" }}
                  className="absolute top-0 bottom-0 w-1 bg-teal-400 shadow-[0_0_20px_#2dd4bf] z-20" />
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {beat >= 4 && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
            <motion.path d="M 400 130 L 250 220" stroke="#475569" strokeWidth="3" variants={drawLine} initial="hidden" animate="visible" />
            <motion.path d="M 400 130 L 550 220" stroke="#475569" strokeWidth="3" variants={drawLine} initial="hidden" animate="visible" />
            <motion.path d="M 550 280 L 680 340" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 6" variants={drawLine} initial="hidden" animate="visible" />
          </svg>
        )}

        <AnimatePresence>
          {beat >= 4 && (
            <>
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }}
                className="absolute top-[80px] left-[320px] w-[160px] h-[50px] bg-slate-800 border-2 border-slate-600 rounded-lg flex items-center justify-center font-mono text-sm text-slate-300 shadow-lg z-10">Assignment</motion.div>
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.4, type: "spring" }}
                className="absolute top-[220px] left-[170px] w-[160px] h-[50px] bg-slate-800 border-2 border-slate-600 rounded-lg flex items-center justify-center font-mono text-sm text-slate-300 shadow-lg z-10">Identifier (hash)</motion.div>
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.4, type: "spring" }}
                className="absolute top-[220px] left-[470px] w-[160px] h-[50px] bg-slate-800 border-2 border-slate-600 rounded-lg flex items-center justify-center font-mono text-sm text-slate-300 shadow-lg z-10">CallExpr (crypto)</motion.div>
            </>
          )}
        </AnimatePresence>

        <motion.div initial={{ x: 100, y: -30, scale: 0.8, opacity: 0 }}
          animate={{ opacity: beat >= 3 ? 1 : 0, x: beat >= 4 ? 210 : 100, y: beat >= 4 ? 90 : -30, scale: beat >= 4 ? 1 : 1.2 }}
          transition={{ duration: 1, type: "spring", stiffness: 60 }}
          className={`absolute w-[140px] h-[60px] flex items-center justify-center font-mono z-20 ${beat >= 4 ? 'bg-[#450a0a] border-2 border-amber-500 rounded-xl shadow-[0_0_30px_rgba(245,158,11,0.4)]' : ''}`}>
          {beat >= 5 && (
            <motion.div initial={{ scale: 1, opacity: 1 }} animate={{ scale: 1.5, opacity: 0 }} transition={{ repeat: Infinity, duration: 1.5 }}
              className="absolute inset-0 border-2 border-amber-500 rounded-xl" />
          )}
          <span className="text-amber-400 font-bold text-lg relative z-10">'md5'</span>
        </motion.div>
      </div>
    </div>
  );
};


// ==========================================
// SCENE 2: CycloneDX CBOM Catalogue
// ==========================================
const Scene2 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 1000); 
    const t2 = setTimeout(() => setBeat(2), 2200); 
    const t3 = setTimeout(() => setBeat(3), 3500); 
    const t4 = setTimeout(() => setBeat(4), 5000); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-[750px] h-[400px] flex items-center justify-center">
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.8, type: "spring" }}
          className="absolute inset-0 bg-[#0f172a] border-2 border-slate-700 rounded-2xl shadow-2xl p-6 flex flex-col overflow-hidden">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <span className="font-mono text-teal-400 font-bold text-sm">CycloneDX v1.5 CBOM Inventory</span>
            <span className="text-xs font-mono text-slate-500">NIST SP 1800-388 Compliant</span>
          </div>
          <div className="grid grid-cols-4 py-3 border-b border-slate-800/80 font-mono text-xs text-slate-400 font-bold">
            <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: beat >= 2 ? 1 : 0 }}>COMPONENT</motion.div>
            <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: beat >= 2 ? 1 : 0 }}>PRIMITIVE</motion.div>
            <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: beat >= 2 ? 1 : 0 }}>CONFIDENCE</motion.div>
            <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: beat >= 2 ? 1 : 0 }}>STATUS</motion.div>
          </div>
          <div className="flex flex-col gap-3 mt-4">
            {[
              { comp: "crypto.createHash", prim: "Hash (MD5)", conf: "High", status: "Vulnerable", color: "text-red-400" },
              { comp: "AES.new()", prim: "Cipher", conf: "High", status: "Secure", color: "text-teal-400" },
              { comp: "RSA.generate", prim: "Asymmetric", conf: "Medium", status: "Review", color: "text-amber-400" },
            ].map((row, i) => (
              <motion.div key={i} initial={{ x: -20, opacity: 0 }}
                animate={{ x: beat >= 3 ? 0 : -20, opacity: beat >= 3 ? 1 : 0 }}
                transition={{ delay: i * 0.4, type: "spring", stiffness: 60 }}
                className="grid grid-cols-4 py-2.5 px-3 bg-slate-900/60 rounded-lg border border-slate-800 font-mono text-xs items-center">
                <span className="text-slate-300">{row.comp}</span>
                <span className="text-slate-400">{row.prim}</span>
                <span className="text-blue-400">{row.conf}</span>
                <span className={`font-bold ${row.color}`}>{row.status}</span>
              </motion.div>
            ))}
          </div>
          <AnimatePresence>
            {beat >= 4 && (
              <motion.div initial={{ scale: 2, opacity: 0, rotate: -15 }} animate={{ scale: 1, opacity: 1, rotate: -5 }}
                transition={{ type: "spring", stiffness: 100 }}
                className="absolute right-8 bottom-8 border-4 border-teal-500 text-teal-400 px-4 py-2 rounded-xl font-mono text-xs font-black uppercase tracking-widest shadow-[0_0_20px_rgba(20,184,166,0.3)] bg-teal-950/80">
                CBOM Verified ✓
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
        <motion.div animate={{ x: [-300, 800] }} transition={{ repeat: Infinity, duration: 3, ease: "easeInOut", repeatDelay: 1 }}
          className="absolute inset-y-0 w-32 bg-gradient-to-r from-transparent via-white/5 to-transparent skew-x-12 pointer-events-none" />
      </div>
    </div>
  );
};


// ==========================================
// SCENE 3: Mosca Risk Engine
// ==========================================
const Scene3 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 800);  
    const t2 = setTimeout(() => setBeat(2), 2000); 
    const t3 = setTimeout(() => setBeat(3), 3200); 
    const t4 = setTimeout(() => setBeat(4), 4500); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, []);

  const drawLine = { hidden: { pathLength: 0, opacity: 0 }, visible: { pathLength: 1, opacity: 1, transition: { duration: 1.2, ease: "easeInOut" } } };

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-[600px] h-[400px]">
        <svg className="absolute inset-0 w-full h-full overflow-visible">
          <motion.line x1="50" y1="350" x2="550" y2="350" stroke="#475569" strokeWidth="3" variants={drawLine} initial="hidden" animate={beat >= 1 ? "visible" : "hidden"} />
          <motion.line x1="50" y1="350" x2="50" y2="50" stroke="#475569" strokeWidth="3" variants={drawLine} initial="hidden" animate={beat >= 1 ? "visible" : "hidden"} />
        </svg>
        <text x="300" y="390" fill="#94a3b8" textAnchor="middle" fontSize="12" fontFamily="monospace">Migration Time (Years) ⟶</text>
        <text x="20" y="200" fill="#94a3b8" textAnchor="middle" fontSize="12" fontFamily="monospace" transform="rotate(-90 20 200)">Shelf Life (Years) ⟶</text>
        <svg className="absolute inset-0 w-full h-full overflow-visible">
          <motion.path d="M 50 320 Q 300 320 530 80" fill="none" stroke="#ef4444" strokeWidth="3" strokeDasharray="8 8"
            initial={{ pathLength: 0 }} animate={{ pathLength: beat >= 2 ? 1 : 0 }} transition={{ duration: 1.5, ease: "easeInOut" }} />
        </svg>
        <AnimatePresence>
          {beat >= 3 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1 }}
              className="absolute top-[50px] right-[70px] w-[250px] h-[150px] bg-red-500/10 border border-red-500/30 rounded-lg pointer-events-none flex items-center justify-center">
              <span className="text-red-400 font-mono text-xs uppercase tracking-widest font-bold">Quantum Risk Zone</span>
            </motion.div>
          )}
        </AnimatePresence>
        <AnimatePresence>
          {beat >= 4 && (
            <motion.div initial={{ scale: 0, x: 50, y: 350 }} animate={{ scale: 1, x: 420, y: 120 }}
              transition={{ type: "spring", stiffness: 80, damping: 12 }}
              className="absolute top-0 left-0 w-28 h-28 bg-[#450a0a] border-2 border-red-500 rounded-xl flex flex-col items-center justify-center shadow-[0_0_40px_rgba(239,68,68,0.5)] z-20">
              <motion.div animate={{ scale: [1, 1.4, 1], opacity: [0.8, 0, 0.8] }} transition={{ repeat: Infinity, duration: 2 }}
                className="absolute inset-0 border-2 border-red-500 rounded-xl pointer-events-none" />
              <span className="font-mono text-red-400 font-black text-xl">MD5</span>
              <span className="text-[10px] text-red-300 uppercase mt-1 font-bold">Critical</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};


// ==========================================
// SCENE 4: NIST PQC Remediation
// ==========================================
const Scene4 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 800);  
    const t2 = setTimeout(() => setBeat(2), 2000); 
    const t3 = setTimeout(() => setBeat(3), 3200); 
    const t4 = setTimeout(() => setBeat(4), 4500); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-[700px] h-[350px] flex items-center justify-center gap-16">
        <AnimatePresence>
          {beat < 3 && (
            <motion.div animate={beat === 1 ? { x: [-3, 3, -3, 3, 0], rotate: [-2, 2, -2, 2, 0] } : { scale: 0, opacity: 0 }}
              transition={beat === 1 ? { repeat: Infinity, duration: 0.2 } : { duration: 0.5 }}
              className="w-36 h-36 bg-[#450a0a] border-2 border-dashed border-red-500 rounded-2xl flex flex-col items-center justify-center shadow-2xl relative">
              {beat === 1 && (<div className="absolute inset-0 border border-teal-400 rounded-2xl animate-ping opacity-30 pointer-events-none" />)}
              <span className="font-mono text-red-400 font-bold text-2xl">MD5</span>
              <span className="text-[10px] text-red-300 uppercase tracking-widest mt-2">Vulnerable</span>
            </motion.div>
          )}
        </AnimatePresence>
        {beat >= 2 && beat < 4 && (
          <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 100, opacity: 1 }} className="h-[2px] bg-slate-600 relative">
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 border-t-2 border-r-2 border-slate-600 rotate-45" />
          </motion.div>
        )}
        <AnimatePresence>
          {beat >= 3 && (
            <motion.div initial={{ scale: 0, rotate: 45, opacity: 0 }} animate={{ scale: 1, rotate: 0, opacity: 1 }}
              transition={{ type: "spring", stiffness: 100, damping: 15 }}
              className="w-44 h-44 bg-teal-950/60 border-2 border-teal-400 rounded-full flex flex-col items-center justify-center shadow-[0_0_50px_rgba(20,184,166,0.3)] relative">
              <motion.div animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.8, 0.4] }} transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
                className="absolute inset-0 border border-teal-400/50 rounded-full pointer-events-none" />
              <span className="font-mono text-teal-300 font-black text-xl">SHA-3</span>
              <span className="text-[9px] text-teal-400 uppercase tracking-widest mt-2 font-bold px-3 py-1 bg-teal-900/50 rounded-full border border-teal-500/40">FIPS 203 Ready</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};


// ==========================================
// SCENE 5: Self-Hosted Architecture
// ==========================================
const Scene5 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 800);  
    const t2 = setTimeout(() => setBeat(2), 2000); 
    const t3 = setTimeout(() => setBeat(3), 3200); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-[750px] h-[350px] flex items-center justify-between px-12">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1 }}
          className="absolute inset-0 border-2 border-teal-500/30 rounded-3xl bg-teal-950/10 pointer-events-none flex items-start justify-center pt-3">
          <span className="font-mono text-[10px] text-teal-400 uppercase tracking-widest bg-teal-950 px-4 py-1 rounded-full border border-teal-500/40 shadow-lg">
            🔒 Air-Gapped Enterprise Network (Data Never Leaves)
          </span>
        </motion.div>
        <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}
          className="w-36 h-36 bg-[#0f172a] border-2 border-slate-700 rounded-2xl flex flex-col items-center justify-center shadow-2xl z-10">
          <span className="font-mono text-slate-200 font-bold text-sm">AST Scanner</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Local Binary</span>
        </motion.div>
        <div className="flex-1 h-[2px] bg-slate-800 relative mx-4">
          {beat >= 2 && (
            <motion.div animate={{ left: ["0%", "100%"] }} transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-teal-400 rounded-full shadow-[0_0_10px_#2dd4bf]" />
          )}
        </div>
        <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.5 }}
          className="w-36 h-36 bg-[#0f172a] border-2 border-slate-700 rounded-2xl flex flex-col items-center justify-center shadow-2xl z-10">
          <span className="font-mono text-slate-200 font-bold text-sm">PostgreSQL</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Local Storage</span>
        </motion.div>
        <div className="flex-1 h-[2px] bg-slate-800 relative mx-4">
          {beat >= 2 && (
            <motion.div animate={{ left: ["0%", "100%"] }} transition={{ repeat: Infinity, duration: 1.5, ease: "linear", delay: 0.7 }}
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-teal-400 rounded-full shadow-[0_0_10px_#2dd4bf]" />
          )}
        </div>
        <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.8 }}
          className="w-36 h-36 bg-teal-950/40 border-2 border-teal-500/60 rounded-2xl flex flex-col items-center justify-center shadow-[0_0_30px_rgba(20,184,166,0.2)] z-10">
          <span className="font-mono text-teal-300 font-bold text-sm">Dashboard</span>
          <span className="text-[10px] text-teal-400 mt-1 font-mono">Local UI</span>
        </motion.div>
      </div>
    </div>
  );
};


// ==========================================
// SCENE 6: Native CI/CD Merge Gate (PURE REACT INTERPOLATED PATH - 100% ALIGNED)
// ==========================================
const Scene6 = () => {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setBeat(1), 800);  
    const t2 = setTimeout(() => setBeat(2), 2000); 
    const t3 = setTimeout(() => setBeat(3), 3500); 
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);

  const drawLine = { hidden: { pathLength: 0, opacity: 0 }, visible: { pathLength: 1, opacity: 1, transition: { duration: 1, ease: "easeInOut" } } };

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-[#060b14] flex items-center justify-center">
      <div className="relative w-full max-w-5xl h-full max-h-[500px] flex items-center justify-center p-6">
        
        <svg className="w-full h-full overflow-visible" viewBox="0 0 1000 500">
          
          {/* Main Branch Line */}
          <motion.line x1="100" y1="250" x2="900" y2="250" stroke="#475569" strokeWidth="6" strokeLinecap="round" variants={drawLine} initial="hidden" animate="visible" />
          
          {/* Feature PR Branch Curve: M 250 250 C 350 420, 650 420, 750 250 */}
          <motion.path 
            d="M 250 250 C 350 420, 650 420, 750 250" 
            fill="none" stroke="#64748b" strokeWidth="4" strokeDasharray="6 6"
            initial={{ pathLength: 0 }} animate={{ pathLength: beat >= 1 ? 1 : 0 }} transition={{ duration: 1, ease: "easeInOut" }} 
          />

          {/* 'main' text label */}
          <text x="920" y="255" fill="#94a3b8" fontSize="16" fontFamily="monospace">main</text>

          {/* FLUID & FLAWLESS REACT MOTION ALONG THE EXACT BEZIER CURVE POINTS */}
          {beat >= 2 && (
            <motion.circle 
              key="scene6-ball"
              r="14" 
              fill="#ef4444" 
              filter="drop-shadow(0px 0px 12px rgba(239, 68, 68, 0.9))"
              initial={{ cx: 250, cy: 250 }}
              animate={{ 
                cx: [250, 285.6, 330.8, 383.2, 440.4, 500, 559.6, 616.8, 669.2, 714.4, 750], 
                cy: [250, 295.9, 331.6, 357.1, 372.4, 377.5, 372.4, 357.1, 331.6, 295.9, 250] 
              }}
              transition={{ duration: 1.5, ease: "linear" }}
            />
          )}

          {/* Compliance Gate Wall (Snapping shut precisely at X: 750 at the exact moment the ball arrives) */}
          {beat >= 3 && (
            <g>
              <motion.line 
                x1="750" y1="180" x2="750" y2="320" 
                stroke="#ef4444" strokeWidth="6" strokeLinecap="round"
                initial={{ scaleY: 0, opacity: 0 }}
                animate={{ scaleY: 1, opacity: 1 }}
                style={{ transformOrigin: "750px 250px" }}
                transition={{ duration: 0.2 }}
              />
              <foreignObject x="780" y="205" width="220" height="90">
                <motion.div 
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 120 }}
                  className="bg-red-950/95 border-2 border-red-500 px-4 py-2.5 rounded-xl shadow-2xl flex flex-col"
                >
                  <span className="text-red-400 font-bold text-xs uppercase tracking-widest font-mono">MERGE BLOCKED</span>
                  <span className="text-[10px] text-red-300 font-mono mt-0.5">Vulnerable Cipher Detected</span>
                </motion.div>
              </foreignObject>
            </g>
          )}
        </svg>

        {/* GitHub Action Trigger Label */}
        {beat >= 1 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="absolute left-1/2 bottom-8 -translate-x-1/2 bg-slate-800 border border-slate-600 px-4 py-1.5 rounded-full font-mono text-xs text-slate-300 shadow-lg">
            ⚡ GitHub Action: ECDAT Scan
          </motion.div>
        )}

      </div>
    </div>
  );
};


// ==========================================
// MAIN SHELL COMPONENT
// ==========================================
export default function ProjectDemoWalkthrough() {
  const [isOpen, setIsOpen] = useState(false);
  const [scene, setScene] = useState(0);

  const scenesLength = 7; 

  // EXPLICIT RESET FIX: When Watch Demo is clicked, reset to Scene 0 before opening.
  const handleOpenDemo = () => {
    setScene(0);
    setIsOpen(true);
  };

  const next = () => setScene((p) => Math.min(p + 1, scenesLength - 1));
  const prev = () => setScene((p) => Math.max(p - 1, 0));

  // Lock document body scroll when modal is open to completely eliminate scrollbars
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Keyboard controls: Arrow keys for navigation, ESC to exit
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'Space') {
        next();
      } else if (e.key === 'ArrowLeft') {
        prev();
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, scene]);

  // Mouse click navigation: Clicking right half moves forward, left half moves backward
  const handleCanvasClick = (e) => {
    const screenWidth = window.innerWidth;
    const clickX = e.clientX;
    if (clickX > screenWidth / 2) {
      next();
    } else {
      prev();
    }
  };

  const ModalOverlay = () => (
    <div 
      onClick={handleCanvasClick}
      style={{ overflow: 'hidden', position: 'fixed', inset: 0, width: '100vw', height: '100vh' }}
      className="z-[99999] flex flex-col font-sans text-slate-50 bg-[#060b14] cursor-pointer select-none"
    >
      
      {/* Top Floating Minimal Bar (ESC instruction & Close) */}
      <div className="absolute top-0 inset-x-0 h-16 flex justify-between items-center px-8 z-30 pointer-events-none">
        <div className="text-xs font-mono tracking-widest text-slate-500 uppercase bg-slate-900/60 px-3 py-1.5 rounded-full border border-slate-800/80 backdrop-blur-md">
          Press <span className="text-teal-400 font-bold">ESC</span> to exit • Click sides or use <span className="text-teal-400 font-bold">Arrow Keys</span> to navigate
        </div>
        <button 
          onClick={(e) => { e.stopPropagation(); setIsOpen(false); }} 
          className="pointer-events-auto p-2 text-slate-400 hover:text-white hover:bg-slate-800/80 rounded-full transition-colors backdrop-blur-md"
        >
          <X size={24} />
        </button>
      </div>

      {/* Main Full-Screen Canvas Area (Zero Scrollbars) */}
      <div className="flex-1 relative w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/20 to-[#060b14]" style={{ overflow: 'hidden' }}>
        <AnimatePresence mode="wait">
          {scene === 0 && <motion.div key="s0" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene0 /></motion.div>}
          {scene === 1 && <motion.div key="s1" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene1 /></motion.div>}
          {scene === 2 && <motion.div key="s2" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene2 /></motion.div>}
          {scene === 3 && <motion.div key="s3" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene3 /></motion.div>}
          {scene === 4 && <motion.div key="s4" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene4 /></motion.div>}
          {scene === 5 && <motion.div key="s5" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene5 /></motion.div>}
          {scene === 6 && <motion.div key="s6" style={{ overflow: 'hidden' }} className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Scene6 /></motion.div>}
        </AnimatePresence>
      </div>

      {/* Bottom Floating Minimal Narration Overlay (Zero PPT Vibes, No Scrollbars) */}
      <div className="absolute bottom-0 inset-x-0 h-[160px] px-12 py-6 bg-gradient-to-t from-[#060b14] via-[#060b14]/90 to-transparent flex flex-col justify-end items-center z-30 pointer-events-none" style={{ overflow: 'hidden' }}>
        <div className="max-w-4xl mx-auto w-full text-center pb-4">
          <AnimatePresence mode="wait">
            <motion.div key={scene} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
              <h2 className="text-xl font-bold text-slate-100 mb-2 tracking-tight">
                {scene === 0 && "The Problem: Cryptographic Sprawl"}
                {scene === 1 && "1. AST Code Scanning (Not Regex)"}
                {scene === 2 && "2. CycloneDX CBOM Catalogue"}
                {scene === 3 && "3. Mosca-Based Risk Engine"}
                {scene === 4 && "4. NIST PQC Remediation"}
                {scene === 5 && "5. Self-Hosted Architecture"}
                {scene === 6 && "6. Native CI/CD Merge Gate"}
              </h2>
              <p className="text-sm text-slate-400 leading-relaxed max-w-2xl mx-auto font-light">
                {scene === 0 && "Enterprises have cryptography scattered everywhere. Without a structural inventory, quantum risk cannot be quantified. ECDAT brings order to the chaos."}
                {scene === 1 && "ECDAT mathematically walks the Abstract Syntax Tree (AST) to map exact execution paths, identifying where weak cryptography is actually used."}
                {scene === 2 && "Raw findings are compiled into a structured Cryptography Bill of Materials (CBOM), satisfying NIST SP 1800-388 compliance."}
                {scene === 3 && "Findings are plotted on a Risk Matrix. By comparing Migration Time vs. Data Shelf Life against the Quantum Threat curve, we isolate critical risks."}
                {scene === 4 && "The engine provides mathematical fixes, mapping vulnerable primitives directly to NIST-approved Post-Quantum algorithms."}
                {scene === 5 && "Your source code never leaves your network. The scanner, Postgres DB, and Dashboard all run locally on-premise."}
                {scene === 6 && "ECDAT integrates natively into GitHub Actions. If a developer pushes vulnerable code, the pipeline physically blocks the merge."}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

    </div>
  );

  return (
    <>
      <button onClick={handleOpenDemo} className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white font-bold py-2 px-5 rounded-md shadow-lg transition-colors border border-teal-500/50">
        <Play size={18} fill="currentColor" /> Watch Demo
      </button>

      {isOpen && createPortal(<ModalOverlay />, document.body)}
    </>
  );
}