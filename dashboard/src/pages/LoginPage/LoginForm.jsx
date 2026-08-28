import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Lock, Activity, Eye, EyeOff, CheckCircle2, ChevronRight, FileSearch, Code2 } from 'lucide-react';
import { z } from 'zod';
import { useAuth } from '../../context/AuthContext';

/* ── Schema ────────────────────────────────────────────────────────────── */
const loginSchema = z.object({
  email: z.string().email('Enter a valid enterprise email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

/* ── Content ───────────────────────────────────────────────────────────── */
const FEATURES = [
  { icon: FileSearch, text: 'AST-powered algorithmic discovery' },
  { icon: Lock,       text: 'Mosca-theorem quantum risk scoring' },
  { icon: Code2,      text: 'CycloneDX 1.6 compliance exports' },
];

export default function LoginForm() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      loginSchema.parse(formData);
      setErrors({});
      setIsLoading(true);

      // Fake network delay for authentic feel
      await new Promise(r => setTimeout(r, 600));

      const success = login(formData.email, formData.password);
      if (success) {
        navigate('/dashboard');
      } else {
        setErrors({ form: 'Invalid credentials. Use demo account.' });
      }
    } catch (err) {
      if (err instanceof z.ZodError) {
        const fieldErrors = {};
        err.errors.forEach(e => { fieldErrors[e.path[0]] = e.message; });
        setErrors(fieldErrors);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoFill = () => {
    setFormData({ email: 'analyst@ecdat.local', password: 'quantum-secure' });
    setErrors({});
  };

  return (
    <div className="min-h-screen font-sans" style={{ background: 'var(--void)', color: 'var(--t1)' }}>
      <div className="grid min-h-screen lg:grid-cols-[1fr_480px]">

        {/* ── Left panel ─────────────────────────────────────────────── */}
        <div className="relative hidden overflow-hidden border-r lg:flex lg:flex-col lg:justify-between lg:p-12"
          style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
          {/* Background elements */}
          <div className="pointer-events-none absolute inset-0">
            <div className="hero-ambient absolute left-1/3 top-1/3 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full" />
            <div className="bg-grid absolute inset-0" />
          </div>

          {/* Logo */}
          <div className="relative flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-bold" style={{ color: 'var(--t1)' }}>ECDAT</div>
              <div className="text-[10px] uppercase tracking-widest font-bold" style={{ color: 'var(--t3)' }}>Enterprise Crypto Scanner</div>
            </div>
          </div>

          {/* Hero quote */}
          <div className="relative max-w-md">
            <div className="mb-8 text-4xl font-black leading-tight" style={{ color: 'var(--t1)' }}>
              Know your cryptography.<br />
              <span style={{
                backgroundImage: 'linear-gradient(135deg, var(--cyan) 0%, var(--purple) 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>Before quantum does.</span>
            </div>
            <div className="space-y-4">
              {FEATURES.map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                    style={{ background: 'var(--cyan-10)', color: 'var(--cyan)' }}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-sm leading-relaxed" style={{ color: 'var(--t2)' }}>{text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="relative text-xs num" style={{ color: 'var(--t4)' }}>
            © 2026 <a href="https://github.com/ctrl-Nix/ECDAT" target="_blank" rel="noopener noreferrer" className="transition-colors hover:underline" style={{ color: 'inherit' }}>Team Port 53</a> · <a href="https://sih.gov.in/" target="_blank" rel="noopener noreferrer" className="transition-colors hover:underline" style={{ color: 'inherit' }}>Smart India Hackathon</a> · <a href="https://sih.gov.in/sih2026PS" target="_blank" rel="noopener noreferrer" className="transition-colors hover:underline" style={{ color: 'inherit' }}>PS 26164</a>
          </div>
        </div>

        {/* ── Right panel (form) ───────────────────────────────────────── */}
        <div className="flex flex-col items-center justify-center p-6 sm:p-10" style={{ background: 'var(--void)' }}>
          <div className="w-full max-w-sm">

            <Link to="/" className="mb-8 flex items-center gap-2 text-sm transition-colors" style={{ color: 'var(--t3)' }} onMouseOver={e=>e.currentTarget.style.color='var(--t1)'} onMouseOut={e=>e.currentTarget.style.color='var(--t3)'}>
              <ChevronRight className="h-4 w-4 rotate-180" /> Back to site
            </Link>

            <div className="mb-8">
              <h1 className="text-2xl font-bold" style={{ color: 'var(--t1)' }}>Sign in to ECDAT</h1>
              <p className="mt-2 text-sm" style={{ color: 'var(--t2)' }}>Access your cryptographic audit ledger</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {errors.form && (
                <div className="rounded-lg border p-3 text-sm flex items-center gap-2"
                  style={{ borderColor: 'rgba(255,61,61,0.25)', background: 'rgba(255,61,61,0.06)', color: 'var(--critical)' }}>
                  <Activity className="h-4 w-4" /> {errors.form}
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider block" style={{ color: 'var(--t3)' }}>Work Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(s => ({ ...s, email: e.target.value }))}
                  placeholder="analyst@enterprise.com"
                  className={`field mono ${errors.email ? 'error' : ''}`}
                />
                {errors.email && <p className="text-xs mt-1" style={{ color: 'var(--critical)' }}>{errors.email}</p>}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider block" style={{ color: 'var(--t3)' }}>Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData(s => ({ ...s, password: e.target.value }))}
                    placeholder="••••••••"
                    className={`field mono ${errors.password ? 'error' : ''}`}
                    style={{ paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--t3)' }}
                    onMouseOver={e=>e.currentTarget.style.color='var(--t2)'} onMouseOut={e=>e.currentTarget.style.color='var(--t3)'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && <p className="text-xs mt-1" style={{ color: 'var(--critical)' }}>{errors.password}</p>}
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-accent-blue" />
                  <span className="text-sm" style={{ color: 'var(--t2)' }}>Remember device</span>
                </label>
                <a href="#" className="text-sm hover:underline" style={{ color: 'var(--cyan)' }}>Recover access</a>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3 mt-2"
              >
                {isLoading ? <Activity className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
                {isLoading ? 'Authenticating...' : 'Sign in securely'}
              </button>
            </form>

            <div className="mt-8 flex items-center gap-3">
              <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
              <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--t3)' }}>or</span>
              <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
            </div>

            <button
              onClick={handleDemoFill}
              className="btn-ghost w-full flex items-center justify-center gap-2 py-3 mt-6 border-dashed"
            >
              <CheckCircle2 className="h-4 w-4" /> Fill demo credentials
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
