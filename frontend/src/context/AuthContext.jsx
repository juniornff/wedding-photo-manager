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
    const storedId = localStorage.getItem('wedding_user_id');
    if (storedId) {
      try {
        const data = await api(`/api/guest/me?user_id=${storedId}`);
        setUser(data);
      } catch {
        const alias = localStorage.getItem('wedding_alias');
        setUser({ id: parseInt(storedId), uuid, alias,
          google_name: localStorage.getItem('wedding_google_name'),
          google_photo: localStorage.getItem('wedding_google_photo'),
        });
      }
    } else {
      const alias = localStorage.getItem('wedding_alias');
      setUser({ uuid, alias });
    }
    setLoading(false);
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
    localStorage.setItem('wedding_user_id', data.id);
    localStorage.setItem('wedding_alias', alias);
    if (data.google_name) localStorage.setItem('wedding_google_name', data.google_name);
    if (data.google_photo) localStorage.setItem('wedding_google_photo', data.google_photo);
    setUser(data);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('wedding_uuid');
    localStorage.removeItem('wedding_user_id');
    localStorage.removeItem('wedding_alias');
    localStorage.removeItem('wedding_google_name');
    localStorage.removeItem('wedding_google_photo');
    setUser(null);
  };

  const isAdmin = Boolean(localStorage.getItem('wedding_is_admin')) || user?.role === 'admin';

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
