import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('ecdat_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('ecdat_token');
    if (token && !user) {
      const fallbackUser = {
        id: 'demo-user',
        email: 'analyst@ecdat.local',
        role: 'Analyst',
      };
      setUser(fallbackUser);
      localStorage.setItem('ecdat_user', JSON.stringify(fallbackUser));
    }

    if (user) {
      localStorage.setItem('ecdat_user', JSON.stringify(user));
    }

    setLoading(false);
  }, [user]);

  const login = (nextUser, token) => {
    localStorage.setItem('ecdat_token', token || 'demo-token');
    localStorage.setItem('ecdat_user', JSON.stringify(nextUser));
    setUser(nextUser);
  };

  const logout = () => {
    localStorage.removeItem('ecdat_token');
    localStorage.removeItem('ecdat_user');
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      login,
      logout,
      isAuthenticated: !!user,
      loading,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
