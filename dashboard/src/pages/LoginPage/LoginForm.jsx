import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Lock, Mail, Server, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';

const schema = z.object({
  email: z.string().email('Enter a valid enterprise email.'),
  password: z.string().min(8, 'Password must be at least 8 characters.'),
});

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [useApiKey, setUseApiKey] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (values) => {
    setSubmitting(true);
    setError('');

    await new Promise((resolve) => setTimeout(resolve, 800));

    if (values.email === 'analyst@ecdat.local' && values.password === 'ecdat1234') {
      const user = { id: 'analyst-1', email: values.email, role: 'Analyst' };
      login(user, 'demo-token');
      navigate('/dashboard');
      return;
    }

    setError('Invalid credentials. Use analyst@ecdat.local / ecdat1234');
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-primary text-slate-100">
      <div className="grid min-h-screen lg:grid-cols-[1.5fr_1fr]">
        <div className="hidden items-center justify-center border-r border-slate-800 bg-slate-950/70 lg:flex">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-blue/15 text-accent-blue">
              <Shield className="h-8 w-8" />
            </div>
            <p className="text-2xl font-medium leading-relaxed text-slate-200">
              “The first step in cryptography is knowing where it lives.”
            </p>
            <p className="mt-4 text-sm text-slate-400">— ECDAT Design Principle</p>
          </div>
        </div>

        <div className="flex items-center justify-center p-6">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900/80 p-8 shadow-xl shadow-slate-950/30">
            <div className="mb-6 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-blue/15 text-accent-blue">
                <Shield className="h-7 w-7" />
              </div>
              <h1 className="mt-4 text-2xl font-bold text-white">Analyst Login</h1>
              <p className="mt-2 text-sm text-slate-400">Access your cryptographic assessment workspace</p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
              <div>
                <label className="mb-2 block text-sm text-slate-300">Work email</label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
                  <input
                    {...register('email')}
                    className={`w-full rounded-lg border bg-slate-950 py-2.5 pl-10 pr-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent-blue ${errors.email ? 'border-red-500' : 'border-slate-700'}`}
                    placeholder="analyst@ecdat.local"
                  />
                </div>
                {errors.email && <p className="mt-2 text-xs text-red-400">{errors.email.message}</p>}
              </div>

              <div>
                <label className="mb-2 block text-sm text-slate-300">Password</label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    className={`w-full rounded-lg border bg-slate-950 py-2.5 pl-10 pr-10 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent-blue ${errors.password ? 'border-red-500' : 'border-slate-700'}`}
                    placeholder="Enter password"
                  />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-3 top-3 text-slate-400 hover:text-slate-200">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && <p className="mt-2 text-xs text-red-400">{errors.password.message}</p>}
              </div>

              <button type="button" onClick={() => setUseApiKey((v) => !v)} className="flex items-center gap-2 text-sm text-slate-300 hover:text-white">
                <Server className="h-4 w-4" />
                {useApiKey ? 'Use password login' : 'Use API key authentication'}
              </button>

              {error && <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

              <button type="submit" disabled={submitting} className="flex w-full items-center justify-center rounded-lg bg-accent-blue px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-blue-400 disabled:opacity-60">
                {submitting ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="mt-6 space-y-3 text-xs text-slate-400">
              <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-emerald-400" /> 256-bit encrypted connection</div>
              <div className="flex items-center gap-2"><Server className="h-4 w-4 text-emerald-400" /> Zero data egress</div>
            </div>

            <div className="mt-6 text-center text-xs text-slate-500">Need help? Contact your security administrator.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
