import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import api from '../lib/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('ecdat_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [token, setToken] = useState(() => localStorage.getItem('ecdat_token'));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      localStorage.setItem('ecdat_user', JSON.stringify(user));
    }
  }, [user]);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', { username, password });
      const userData = { username: data.username, role: data.user_role };
      localStorage.setItem('ecdat_token', data.access_token);
      localStorage.setItem('ecdat_user', JSON.stringify(userData));
      setToken(data.access_token);
      setUser(userData);
      return userData;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('ecdat_token');
    localStorage.removeItem('ecdat_user');
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      token,
      login,
      logout,
      isAuthenticated: !!user && !!token,
      loading,
    }),
    [user, token, loading],
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
