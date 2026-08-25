import { Suspense, lazy, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, LoaderCircle } from 'lucide-react';
import { useAuth } from './context/AuthContext.jsx';

const LandingPage = lazy(() => import('./pages/LandingPage/index.jsx'));
const LoginPage = lazy(() => import('./pages/LoginPage/index.jsx'));
const DashboardPage = lazy(() => import('./pages/DashboardPage/index.jsx'));

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
          className={`sticky top-0 z-50 border-b border-slate-700/80 bg-primary/80 backdrop-blur-md ${isScrolled ? 'shadow-lg shadow-slate-950/20' : ''}`}
        >
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
            <button onClick={() => navigate('/')} className="flex items-center gap-3 text-left">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-blue/20 text-accent-blue">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-white">ECDAT</div>
              </div>
            </button>
            <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
              <button onClick={() => navigate('/#product')} className="hover:text-white">Product</button>
              <button onClick={() => navigate('/#scanner')} className="hover:text-white">Scanner</button>
              <button onClick={() => navigate('/#compliance')} className="hover:text-white">Compliance</button>
              <button onClick={() => navigate('/#docs')} className="hover:text-white">Docs</button>
            </nav>
            <div className="flex items-center gap-3">
              <button onClick={() => navigate('/login')} className="hidden rounded-full border border-slate-600 px-4 py-2 text-sm font-medium text-slate-100 hover:border-slate-500 sm:inline-flex">Log in</button>
              <button onClick={() => navigate('/login')} className="rounded-full bg-accent-blue px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-blue-400">Get started</button>
            </div>
          </div>
        </motion.header>
      )}

      <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-primary text-slate-100">Loading…</div>}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </>
  );
}

export default function App() {
  return <AppShell />;
}
