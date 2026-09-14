import { useState, useEffect, useCallback } from 'react';
import { AuthContext } from './AuthContext';
import { api, API_BASE } from '../api';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const checkSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/me`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        if (data.is_admin) {
          localStorage.setItem('wedding_is_admin', 'true');
          setIsAdmin(true);
          if (data.user_id) {
            localStorage.setItem('wedding_uuid', data.uuid);
            localStorage.setItem('wedding_user_id', data.user_id);
            localStorage.setItem('wedding_alias', data.alias);
            setUser({ id: data.user_id, uuid: data.uuid, alias: data.alias });
            setLoading(false);
            return;
          }
        } else {
          localStorage.removeItem('wedding_is_admin');
          setIsAdmin(false);
        }
      } else {
        localStorage.removeItem('wedding_is_admin');
        setIsAdmin(false);
      }
    } catch {
      localStorage.removeItem('wedding_is_admin');
      setIsAdmin(false);
    }

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
    fetch(`${API_BASE}/api/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
    localStorage.removeItem('wedding_uuid');
    localStorage.removeItem('wedding_user_id');
    localStorage.removeItem('wedding_alias');
    localStorage.removeItem('wedding_google_name');
    localStorage.removeItem('wedding_google_photo');
    localStorage.removeItem('wedding_is_admin');
    setUser(null);
    setIsAdmin(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkSession, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}