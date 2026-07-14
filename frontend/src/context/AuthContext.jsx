import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkSession = useCallback(async () => {
    const uuid = localStorage.getItem('wedding_uuid');
    if (!uuid) {
      setLoading(false);
      return;
    }
    try {
      const data = await api('/api/guest/me');
      setUser(data);
    } catch {
      localStorage.removeItem('wedding_uuid');
      localStorage.removeItem('wedding_alias');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const login = async (alias) => {
    const data = await api('/api/guest', {
      method: 'POST',
      body: JSON.stringify({ alias }),
    });
    localStorage.setItem('wedding_uuid', data.uuid);
    localStorage.setItem('wedding_alias', alias);
    setUser(data);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('wedding_uuid');
    localStorage.removeItem('wedding_alias');
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkSession, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
