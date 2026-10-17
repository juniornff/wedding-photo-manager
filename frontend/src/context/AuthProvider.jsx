import { useState, useEffect, useCallback } from 'react';
import { AuthContext } from './AuthContext';
import { api, API_BASE } from '../api';

function safeGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // localStorage no disponible
  }
}

function safeRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // localStorage no disponible
  }
}

function isValidId(value) {
  return /^\d+$/.test(String(value ?? ''));
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const checkSession = useCallback(async () => {
    const params = new URLSearchParams(window.location.search);
    const googleUserId = params.get('google_user');
    if (googleUserId && isValidId(googleUserId)) {
      try {
        const data = await api(`/api/guest/me?user_id=${googleUserId}`);
        safeSet('wedding_uuid', data.uuid);
        safeSet('wedding_user_id', data.id);
        if (data.alias) safeSet('wedding_alias', data.alias);
        if (data.google_name) safeSet('wedding_google_name', data.google_name);
        if (data.google_photo) safeSet('wedding_google_photo', data.google_photo);
        setUser(data);
      } catch {
        setUser(null);
      }
      window.history.replaceState({}, '', window.location.pathname);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/admin/me`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        if (data.is_admin) {
          safeSet('wedding_is_admin', 'true');
          setIsAdmin(true);
          if (data.user_id) {
            safeSet('wedding_uuid', data.uuid);
            safeSet('wedding_user_id', data.user_id);
            safeSet('wedding_alias', data.alias);
            if (data.role) safeSet('wedding_role', data.role);
            setUser({
              id: data.user_id,
              uuid: data.uuid,
              alias: data.alias,
              role: data.role,
              google_name: data.google_name,
              google_photo: data.google_photo,
            });
            setLoading(false);
            return;
          }
        } else {
          safeRemove('wedding_is_admin');
          setIsAdmin(false);
        }
      } else {
        safeRemove('wedding_is_admin');
        setIsAdmin(false);
      }
    } catch {
      safeRemove('wedding_is_admin');
      setIsAdmin(false);
    }

    const uuid = safeGet('wedding_uuid');
    if (!uuid) {
      setLoading(false);
      return;
    }
    const storedId = safeGet('wedding_user_id');
    if (storedId && isValidId(storedId)) {
      try {
        const data = await api(`/api/guest/me?user_id=${storedId}`);
        if (data.role) safeSet('wedding_role', data.role);
        setUser(data);
      } catch {
        const alias = safeGet('wedding_alias');
        setUser({ id: parseInt(storedId, 10), uuid, alias,
          role: safeGet('wedding_role'),
          google_name: safeGet('wedding_google_name'),
          google_photo: safeGet('wedding_google_photo'),
        });
      }
    } else {
      const alias = safeGet('wedding_alias');
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
    safeSet('wedding_uuid', data.uuid);
    safeSet('wedding_user_id', data.id);
    safeSet('wedding_alias', alias);
    if (data.role) safeSet('wedding_role', data.role);
    if (data.google_name) safeSet('wedding_google_name', data.google_name);
    if (data.google_photo) safeSet('wedding_google_photo', data.google_photo);
    setUser(data);
    return data;
  };

  const logout = () => {
    fetch(`${API_BASE}/api/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
    safeRemove('wedding_uuid');
    safeRemove('wedding_user_id');
    safeRemove('wedding_alias');
    safeRemove('wedding_google_name');
    safeRemove('wedding_google_photo');
    safeRemove('wedding_is_admin');
    safeRemove('wedding_role');
    setUser(null);
    setIsAdmin(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkSession, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}