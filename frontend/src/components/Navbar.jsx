import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { api } from '../api';

export default function Navbar() {
  const { user, loading, login, logout, isAdmin } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [alias, setAlias] = useState('');
  const [error, setError] = useState('');
  const [myTable, setMyTable] = useState(null);

  const fetchMyTable = useCallback(async () => {
    if (!user?.id) {
      setMyTable(null);
      return;
    }
    try {
      const data = await api(`/api/secret-photographer/my-table?user_id=${user.id}`);
      setMyTable(data);
    } catch {
      setMyTable(null);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchMyTable();
  }, [fetchMyTable]);

  useEffect(() => {
    window.addEventListener('table-assigned', fetchMyTable);
    return () => window.removeEventListener('table-assigned', fetchMyTable);
  }, [fetchMyTable]);

  useEffect(() => {
    if (!loading && !user && !isAdmin) {
      setShowLogin(true);
    }
  }, [loading, user, isAdmin]);

  useEffect(() => {
    const handler = () => setShowLogin(true);
    window.addEventListener('show-login', handler);
    return () => window.removeEventListener('show-login', handler);
  }, []);

  const closeLogin = () => {
    setShowLogin(false);
    setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!alias.trim()) return;
    try {
      await login(alias.trim());
      setShowLogin(false);
      setAlias('');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-[var(--color-secondary)]">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-4">
        <Link to="/" className="font-bold text-lg" style={{ color: 'var(--color-primary)' }}>
          Wedding Photo
        </Link>
        <Link
          to="/fotografo-secreto"
          className="text-sm text-gray-500 hover:text-[var(--color-accent)] transition"
        >
          Fotógrafo Secreto
        </Link>
        {myTable && (
          <Link
            to={`/fotografo-secreto/${myTable.qr_code}`}
            className="text-xs px-3 py-1 rounded-full border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white transition"
          >
            Mi Mesa
          </Link>
        )}
      </div>

        <div className="flex items-center gap-3">
          {(user || isAdmin) ? (
            <>
              <div className="flex items-center gap-2">
                {user?.google_photo && (
                  <img src={user.google_photo} alt="" className="w-7 h-7 rounded-full object-cover" />
                )}
                <span className="text-sm font-medium truncate max-w-28">
                  {user?.google_name || user?.alias || 'Admin'}
                </span>
              </div>
              {isAdmin && (
                <Link
                  to="/admin"
                  className="text-xs px-3 py-1 rounded-full border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white transition"
                >
                  Admin
                </Link>
              )}
              {user && !user.google_name && !user.google_photo && (
                <a
                  href={`/api/google?user_id=${user.id}`}
                  className="text-xs px-3 py-1 rounded-full border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
                >
                  Conectar Google
                </a>
              )}
              <button
                onClick={logout}
                className="text-xs text-gray-400 hover:text-gray-600 transition cursor-pointer"
              >
                Salir
              </button>
            </>
          ) : (
            <button
              onClick={() => setShowLogin(true)}
              className="text-sm px-4 py-1.5 rounded-full bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer"
            >
              Entrar
            </button>
          )}
        </div>
      </div>

      {showLogin && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 px-4 pt-[15vh]" onClick={closeLogin}>
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold mb-4">¿Cómo te llamas?</h2>
            <form onSubmit={handleLogin}>
              <input
                type="text"
                value={alias}
                onChange={(e) => setAlias(e.target.value)}
                placeholder="Tu nombre o apodo"
                className="w-full border rounded-lg p-2.5 text-sm mb-3"
                autoFocus
                maxLength={50}
              />
              {error && <p className="text-red-500 text-xs mb-2">{error}</p>}
              <button
                type="submit"
                className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:brightness-110 transition cursor-pointer"
              >
                Entrar
              </button>
            </form>
            <div className="mt-3 text-center">
              <span className="text-xs text-gray-400">o</span>
            </div>
            <a
              href="/api/google"
              className="mt-3 w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 transition"
            >
              Iniciar sesión con Google
            </a>
          </div>
        </div>
      )}
    </nav>
  );
}
