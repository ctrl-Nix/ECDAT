import ProjectDemoWalkthrough from './components/ProjectDemoWalkthrough';
import { Suspense, lazy, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, LoaderCircle } from 'lucide-react';
import { useAuth } from './context/AuthContext.jsx';

const LandingPage = lazy(() => import('./pages/LandingPage/index.jsx'));
const LoginPage = lazy(() => import('./pages/LoginPage/index.jsx'));
const DashboardPage = lazy(() => import('./pages/DashboardPage/index.jsx'));
const FindingsPage = lazy(() => import('./pages/FindingsPage/index.jsx'));

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-primary text-slate-100">
        <LoaderCircle className="h-10 w-10 animate-spin text-accent-blue" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function PublicOnlyRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-primary text-slate-100">
        <LoaderCircle className="h-10 w-10 animate-spin text-accent-blue" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [pathname]);

  return null;
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 12);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (location.pathname === '/dashboard' && !localStorage.getItem('ecdat_token')) {
      navigate('/login');
    }
  }, [location.pathname, navigate]);

  return (
    <>
      <ScrollToTop />
      {location.pathname !== '/' && location.pathname !== '/dashboard' && (
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`sticky top-0 z-50 border-b border-rose-200/80 bg-white/90 backdrop-blur-md ${isScrolled ? 'shadow-md shadow-slate-950/5' : ''}`}
        >
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
            <button onClick={() => navigate('/')} className="flex items-center gap-3 text-left">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-rose-100 text-rose-600">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-bold text-slate-900">ECDAT</div>
              </div>
            </button>
            <nav className="hidden items-center gap-8 text-sm font-medium text-slate-700 md:flex">
              <button onClick={() => navigate('/#product')} className="hover:text-slate-950 transition-colors">Product</button>
              <button onClick={() => navigate('/#scanner')} className="hover:text-slate-950 transition-colors">Scanner</button>
              <button onClick={() => navigate('/#compliance')} className="hover:text-slate-950 transition-colors">Compliance</button>
              <button onClick={() => navigate('/#docs')} className="hover:text-slate-950 transition-colors">Docs</button>
            </nav>
            <div className="flex items-center gap-3">
              <button onClick={() => navigate('/login')} className="hidden rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 hover:border-slate-400 hover:bg-slate-50 sm:inline-flex">Log in</button>
              <button onClick={() => navigate('/login')} className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Get started</button>
            </div>
          </div>
        </motion.header>
      )}

      <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-primary text-slate-100">Loading…</div>}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/dashboard/findings" element={<ProtectedRoute><FindingsPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </>
  );
}

export default function App() {
  return <AppShell />;
}
