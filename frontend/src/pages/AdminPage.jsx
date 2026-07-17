import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, apiUpload, API_BASE } from '../api';

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition cursor-pointer ${
        active
          ? 'bg-[var(--color-primary)] text-white'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {children}
    </button>
  );
}

function DashboardTab() {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    api('/api/admin/dashboard').then(setStats).catch(() => {});
  }, []);
  if (!stats) return <p className="text-gray-400">Cargando...</p>;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[
        { label: 'Fotos totales', value: stats.total_photos },
        { label: 'Usuarios', value: stats.total_users },
        { label: 'Mesas', value: stats.total_tables },
        { label: 'Retos', value: stats.total_challenges },
      ].map((s) => (
        <div key={s.label} className="bg-white rounded-xl p-4 shadow-sm text-center">
          <p className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>{s.value ?? 0}</p>
          <p className="text-xs text-gray-500">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

function ColorField({ label, value, onChange }) {
  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-medium w-24 shrink-0">{label}</label>
      <input
        type="color"
        value={value || '#000000'}
        onChange={(e) => onChange(e.target.value)}
        className="w-10 h-10 rounded cursor-pointer border-0 p-0.5"
      />
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="border rounded-lg p-2 text-sm font-mono flex-1"
        placeholder="#000000"
        maxLength={7}
      />
    </div>
  );
}

function WeddingInfoTab() {
  const [form, setForm] = useState({ novio1_name: '', novio2_name: '', wedding_date: '', color_primary: '', color_secondary: '', color_accent: '', carousel_interval: 5 });
  const [msg, setMsg] = useState('');

  useEffect(() => {
    api('/api/wedding-info').then((data) => {
      const colors = (data.color_scheme || '').split(',').map((c) => c.trim());
      setForm({
        novio1_name: data.novio1_name || '',
        novio2_name: data.novio2_name || '',
        wedding_date: data.wedding_date || '',
        color_primary: colors[0] || '',
        color_secondary: colors[1] || '',
        color_accent: colors[2] || '',
        carousel_interval: data.carousel_interval ?? 5,
      });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    try {
      const parts = [form.color_primary, form.color_secondary, form.color_accent].filter(Boolean);
      await api('/api/admin/wedding-info', {
        method: 'PUT',
        body: JSON.stringify({
          novio1_name: form.novio1_name || null,
          novio2_name: form.novio2_name || null,
          wedding_date: form.wedding_date || null,
          color_scheme: parts.length > 0 ? parts.join(',') : null,
          carousel_interval: form.carousel_interval || null,
        }),
      });
      setMsg('Información actualizada');
      setTimeout(() => setMsg(''), 2000);
    } catch (err) {
      setMsg('Error: ' + err.message);
    }
  };

  return (
    <div className="max-w-lg space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Nombre del primer contrayente</label>
        <input value={form.novio1_name} onChange={(e) => setForm({ ...form, novio1_name: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Nombre del segundo contrayente</label>
        <input value={form.novio2_name} onChange={(e) => setForm({ ...form, novio2_name: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Fecha</label>
        <input type="date" value={form.wedding_date} onChange={(e) => setForm({ ...form, wedding_date: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div className="space-y-3 pt-2 border-t border-gray-200">
        <p className="text-sm font-semibold">Esquema de color</p>
        <ColorField label="Principal" value={form.color_primary} onChange={(v) => setForm({ ...form, color_primary: v })} />
        <ColorField label="Secundario" value={form.color_secondary} onChange={(v) => setForm({ ...form, color_secondary: v })} />
        <ColorField label="Terciario" value={form.color_accent} onChange={(v) => setForm({ ...form, color_accent: v })} />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Intervalo del carrusel (segundos)</label>
        <input type="number" min="2" max="60" value={form.carousel_interval} onChange={(e) => setForm({ ...form, carousel_interval: parseInt(e.target.value) || 5 })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm cursor-pointer">Guardar</button>
      {msg && <p className="text-sm text-green-600">{msg}</p>}
    </div>
  );
}

function CarouselTab() {
  const [photos, setPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    api('/api/carousel')
      .then((data) => setPhotos(data.items || data.photos || data || []))
      .catch(() => {});
  }, []);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const data = await apiUpload('/api/admin/carousel', fd);
      setPhotos((prev) => [...prev, data]);
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api(`/api/admin/carousel/${id}`, { method: 'DELETE' });
      setPhotos((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleMove = async (id, direction) => {
    try {
      const idx = photos.findIndex((p) => p.id === id);
      if (idx === -1) return;
      const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= photos.length) return;
      const reordered = [...photos];
      [reordered[idx], reordered[swapIdx]] = [reordered[swapIdx], reordered[idx]];
      await api('/api/admin/carousel/reorder', {
        method: 'PUT',
        body: JSON.stringify(reordered.map((p, i) => ({ id: p.id, sort_order: i }))),
      });
      setPhotos(reordered);
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <input type="file" accept="image/*" onChange={handleUpload} disabled={uploading} className="text-sm" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {photos.map((photo, idx) => (
          <div key={photo.id || idx} className="bg-white rounded-xl overflow-hidden shadow-sm">
            <img src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : photo.path ? `${API_BASE}/api/uploads/${photo.path}` : ''} alt="" className="aspect-video object-cover w-full" />
            <div className="p-2 flex justify-between items-center">
              <div className="flex gap-1">
                <button onClick={() => handleMove(photo.id, 'up')} className="text-xs px-2 py-1 bg-gray-100 rounded cursor-pointer" disabled={idx === 0}>↑</button>
                <button onClick={() => handleMove(photo.id, 'down')} className="text-xs px-2 py-1 bg-gray-100 rounded cursor-pointer" disabled={idx === photos.length - 1}>↓</button>
              </div>
              <button onClick={() => handleDelete(photo.id)} className="text-xs px-2 py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TablesTab() {
  const [tables, setTables] = useState([]);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    api('/api/admin/tables').then(setTables).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const table = await api('/api/admin/tables', {
        method: 'POST',
        body: JSON.stringify({ name: newName.trim() }),
      });
      setTables((prev) => [...prev, table]);
      setNewName('');
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api(`/api/admin/tables/${id}`, { method: 'DELETE' });
      setTables((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Nombre de la mesa"
          className="border rounded-lg p-2 text-sm flex-1"
        />
        <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm cursor-pointer">Crear</button>
      </div>
      <div className="space-y-2">
        {tables.map((table) => (
          <div key={table.id} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm">
            <div>
              <p className="font-medium text-sm">{table.name || `Mesa ${table.number}`}</p>
              <p className="text-xs text-gray-400">QR: {table.qr_code}</p>
            </div>
            <div className="flex gap-2">
              {table.qr_url && (
                <a href={`${API_BASE}${table.qr_url}`} download className="text-xs px-3 py-1 bg-gray-100 rounded cursor-pointer">QR</a>
              )}
              <button onClick={() => handleDelete(table.id)} className="text-xs px-3 py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChallengesTab() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    api('/api/admin/tables').then(setTables).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedTable) return;
    api(`/api/admin/challenges?table_id=${selectedTable}`)
      .then(setChallenges)
      .catch(() => {});
  }, [selectedTable]);

  const handleCreate = async () => {
    if (!newTitle.trim() || !selectedTable) return;
    try {
      const chal = await api('/api/admin/challenges', {
        method: 'POST',
        body: JSON.stringify({ table_id: selectedTable, description: newTitle.trim(), sort_order: 0 }),
      });
      setChallenges((prev) => [...prev, chal]);
      setNewTitle('');
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api(`/api/admin/challenges/${id}`, { method: 'DELETE' });
      setChallenges((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleUnlock = async (id) => {
    try {
      const updated = await api(`/api/admin/challenges/${id}/unlock`, { method: 'PUT' });
      setChallenges((prev) => prev.map((c) => c.id === id ? updated : c));
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Seleccionar mesa</label>
        <select
          value={selectedTable || ''}
          onChange={(e) => setSelectedTable(Number(e.target.value) || null)}
          className="border rounded-lg p-2 text-sm"
        >
          <option value="">-- Selecciona --</option>
          {tables.map((t) => (
            <option key={t.id} value={t.id}>{t.name || `Mesa ${t.number || t.id}`}</option>
          ))}
        </select>
      </div>

      {selectedTable && (
        <>
          <div className="flex gap-2 mb-4">
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Descripción del reto"
              className="border rounded-lg p-2 text-sm flex-1"
            />
            <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm cursor-pointer">Crear</button>
          </div>
          <div className="space-y-2">
            {challenges.map((ch) => (
              <div key={ch.id} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm">
                <div>
                  <p className="font-medium text-sm">{ch.description || `Reto ${ch.id}`}</p>
                  <p className="text-xs text-gray-400">{ch.photo_count || 0}/{ch.max_photos || 0} fotos{ch.locked ? ' (desbloqueado)' : ''}</p>
                </div>
                <div className="flex gap-2">
                  {ch.photo_count >= ch.max_photos && ch.max_photos > 0 && !ch.locked && (
                    <button onClick={() => handleUnlock(ch.id)} className="text-xs px-3 py-1 bg-yellow-100 text-yellow-700 rounded cursor-pointer">Desbloquear</button>
                  )}
                  <button onClick={() => handleDelete(ch.id)} className="text-xs px-3 py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function GalleryTab() {
  const [photos, setPhotos] = useState([]);
  const [selectedIdx, setSelectedIdx] = useState(null);

  const loadPhotos = () => {
    api('/api/gallery?offset=0&limit=50')
      .then((data) => setPhotos(data.items || data.photos || data || []))
      .catch(() => {});
  };

  useEffect(loadPhotos, []);

  const selected = selectedIdx !== null ? photos[selectedIdx] : null;

  useEffect(() => {
    if (selectedIdx === null) return;
    const handler = (e) => {
      if (e.key === 'Escape') setSelectedIdx(null);
      if (e.key === 'ArrowLeft') setSelectedIdx((i) => (i > 0 ? i - 1 : i));
      if (e.key === 'ArrowRight') setSelectedIdx((i) => (i < photos.length - 1 ? i + 1 : i));
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedIdx, photos.length]);

  const handleDelete = async (id) => {
    if (!confirm('¿Eliminar esta foto?')) return;
    try {
      await api(`/api/admin/gallery/${id}`, { method: 'DELETE' });
      if (selected?.id === id) setSelectedIdx(null);
      setPhotos((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  if (photos.length === 0) {
    return <p className="text-center text-gray-400 py-12">No hay fotos en la galería</p>;
  }

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {photos.map((photo, idx) => (
          <div key={photo.id || idx} className="bg-white rounded-xl overflow-hidden shadow-sm">
            <button onClick={() => setSelectedIdx(idx)} className="w-full cursor-pointer border-0 p-0">
              <img src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : photo.path ? `${API_BASE}/api/uploads/${photo.path}` : ''} alt="" className="aspect-square object-cover w-full" loading="lazy" />
            </button>
            <div className="p-2 space-y-1">
              <div className="flex items-center gap-1.5 min-w-0">
                {photo.user_google_photo && (
                  <img src={photo.user_google_photo} alt="" className="w-5 h-5 rounded-full object-cover shrink-0" />
                )}
                <span className="text-xs truncate">{photo.user_google_name || photo.user_alias || 'Anónimo'}</span>
              </div>
              {photo.message && (
                <p className="text-xs text-gray-500 truncate">{photo.message}</p>
              )}
              <button onClick={() => handleDelete(photo.id)} className="w-full text-xs py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedIdx(null)}
        >
          <div
            className="relative max-w-3xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-end mb-2">
              <button onClick={() => setSelectedIdx(null)} className="text-white text-2xl hover:opacity-70 cursor-pointer">&times;</button>
            </div>

            <div className="relative flex items-center justify-center bg-black/40 rounded-t-xl overflow-hidden min-h-[300px]">
              {selectedIdx > 0 && (
                <button onClick={() => setSelectedIdx(selectedIdx - 1)} className="absolute left-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2">‹</button>
              )}
              <img
                src={selected.path ? `${API_BASE}/api/uploads/${selected.path}` : ''}
                alt={selected.message || 'Foto'}
                className="max-w-full max-h-[70vh] object-contain"
              />
              {selectedIdx < photos.length - 1 && (
                <button onClick={() => setSelectedIdx(selectedIdx + 1)} className="absolute right-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2">›</button>
              )}
            </div>

            <div className="bg-white rounded-b-xl p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 min-w-0">
                {selected.user_google_photo && (
                  <img src={selected.user_google_photo} alt="" className="w-6 h-6 rounded-full object-cover shrink-0" />
                )}
                <span className="text-sm font-medium truncate">
                  {selected.user_google_name || selected.user_alias || 'Anónimo'}
                </span>
                {selected.message && (
                  <span className="text-sm text-gray-500 truncate">&mdash; {selected.message}</span>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                <a
                  href={`${API_BASE}/api/gallery/${selected.id}/download`}
                  download
                  className="text-sm px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer"
                >
                  Descargar
                </a>
                <button
                  onClick={() => handleDelete(selected.id)}
                  className="text-sm px-4 py-2 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 transition cursor-pointer"
                >
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function WinnerTab() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [challengePhotos, setChallengePhotos] = useState([]);

  useEffect(() => {
    api('/api/admin/tables').then(setTables).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedTable) return;
    api(`/api/admin/tables/${selectedTable}/photos`)
      .then((data) => setChallengePhotos(data || []))
      .catch(() => {});
  }, [selectedTable]);

  const handleSelectWinner = async (tableId) => {
    try {
      await api(`/api/admin/select-winner?table_id=${tableId}`, { method: 'POST' });
      alert('¡Ganador seleccionado!');
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Seleccionar mesa</label>
        <select
          value={selectedTable || ''}
          onChange={(e) => setSelectedTable(Number(e.target.value) || null)}
          className="border rounded-lg p-2 text-sm"
        >
          <option value="">-- Selecciona --</option>
          {tables.map((t) => (
            <option key={t.id} value={t.id}>{t.name || `Mesa ${t.number || t.id}`}</option>
          ))}
        </select>
      </div>

      {challengePhotos.map((ch) => (
        <div key={ch.challenge_id} className="mb-6">
          <h3 className="font-medium text-sm mb-2">{ch.challenge_description || `Reto ${ch.challenge_id}`}</h3>
          {ch.photos && ch.photos.length > 0 ? (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {ch.photos.map((photo, idx) => (
                <img
                  key={photo.id || idx}
                  src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : photo.path ? `${API_BASE}/api/uploads/${photo.path}` : ''}
                  alt=""
                  className="aspect-square object-cover rounded-lg"
                />
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400">Sin fotos</p>
          )}
        </div>
      ))}

      {selectedTable && (
        <button
          onClick={() => handleSelectWinner(selectedTable)}
          className="px-6 py-3 rounded-lg bg-[var(--color-primary)] text-white font-medium cursor-pointer"
        >
          Seleccionar como ganador
        </button>
      )}
    </div>
  );
}

function AdminLoginForm() {
  const { checkSession } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/admin/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error del servidor' }));
        throw new Error(err.detail || 'Credenciales inválidas');
      }
      await checkSession();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--color-bg)]">
      <div className="bg-white rounded-2xl p-8 w-full max-w-sm shadow-lg">
        <h1 className="text-2xl font-bold mb-6 text-center">Panel de Administración</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Correo electrónico</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@ejemplo.com"
              className="w-full border rounded-lg p-2.5 text-sm"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full border rounded-lg p-2.5 text-sm"
            />
          </div>
          {error && <p className="text-red-500 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:brightness-110 transition disabled:opacity-50 cursor-pointer"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        <div className="mt-4 text-center">
          <span className="text-xs text-gray-400">o</span>
        </div>
        <a
          href="/api/google"
          className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 transition"
        >
          Iniciar sesión con Google
        </a>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const { isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <p className="text-gray-400">Verificando...</p>
      </div>
    );
  }

  if (!isAdmin) {
    return <AdminLoginForm />;
  }

  const [tab, setTab] = useState('dashboard');

  const tabs = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'info', label: 'Info Boda' },
    { key: 'carousel', label: 'Carrusel' },
    { key: 'tables', label: 'Mesas' },
    { key: 'challenges', label: 'Retos' },
    { key: 'gallery', label: 'Galería' },
    { key: 'winner', label: 'Ganador' },
  ];

  return (
    <div className="min-h-screen max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Panel de Administración</h1>

      <div className="flex flex-wrap gap-2 mb-6">
        {tabs.map((t) => (
          <TabButton key={t.key} active={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
          </TabButton>
        ))}
      </div>

      <div className="bg-white/50 rounded-2xl p-6 shadow-sm">
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'info' && <WeddingInfoTab />}
        {tab === 'carousel' && <CarouselTab />}
        {tab === 'tables' && <TablesTab />}
        {tab === 'challenges' && <ChallengesTab />}
        {tab === 'gallery' && <GalleryTab />}
        {tab === 'winner' && <WinnerTab />}
      </div>
    </div>
  );
}
