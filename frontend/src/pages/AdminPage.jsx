import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, apiUpload } from '../api';

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

function WeddingInfoTab() {
  const [form, setForm] = useState({ couple_name1: '', couple_name2: '', date: '', color_scheme: '' });
  const [msg, setMsg] = useState('');

  useEffect(() => {
    api('/api/wedding-info').then(setForm).catch(() => {});
  }, []);

  const handleSave = async () => {
    try {
      await api('/api/admin/wedding-info', {
        method: 'PUT',
        body: JSON.stringify(form),
      });
      setMsg('Información actualizada');
      setTimeout(() => setMsg(''), 2000);
    } catch (err) {
      setMsg('Error: ' + err.message);
    }
  };

  return (
    <div className="max-w-md space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Nombre del primer contrayente</label>
        <input value={form.couple_name1 || ''} onChange={(e) => setForm({ ...form, couple_name1: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Nombre del segundo contrayente</label>
        <input value={form.couple_name2 || ''} onChange={(e) => setForm({ ...form, couple_name2: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Fecha</label>
        <input value={form.date || ''} onChange={(e) => setForm({ ...form, date: e.target.value })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Esquema de color (opcional)</label>
        <input value={form.color_scheme || ''} onChange={(e) => setForm({ ...form, color_scheme: e.target.value })} className="w-full border rounded-lg p-2 text-sm" placeholder="ej: #ff0000,#00ff00" />
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
      const data = await apiUpload('/api/admin/carousel/upload', fd);
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
      await api(`/api/admin/carousel/${id}/move`, {
        method: 'PUT',
        body: JSON.stringify({ direction }),
      });
      const data = await api('/api/carousel');
      setPhotos(data.items || data.photos || data || []);
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
            <img src={photo.thumbnail_url || photo.url} alt="" className="aspect-video object-cover w-full" />
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
                <a href={table.qr_url} download className="text-xs px-3 py-1 bg-gray-100 rounded cursor-pointer">QR</a>
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
    api(`/api/admin/tables/${selectedTable}/challenges`)
      .then(setChallenges)
      .catch(() => {});
  }, [selectedTable]);

  const handleCreate = async () => {
    if (!newTitle.trim() || !selectedTable) return;
    try {
      const chal = await api(`/api/admin/tables/${selectedTable}/challenges`, {
        method: 'POST',
        body: JSON.stringify({ title: newTitle.trim() }),
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
      await api(`/api/admin/challenges/${id}/unlock`, { method: 'PUT' });
      setChallenges((prev) => prev.map((c) => c.id === id ? { ...c, locked: false } : c));
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
            <option key={t.id} value={t.id}>{t.name || `Mesa ${t.number}`}</option>
          ))}
        </select>
      </div>

      {selectedTable && (
        <>
          <div className="flex gap-2 mb-4">
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Título del reto"
              className="border rounded-lg p-2 text-sm flex-1"
            />
            <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm cursor-pointer">Crear</button>
          </div>
          <div className="space-y-2">
            {challenges.map((ch) => (
              <div key={ch.id} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm">
                <div>
                  <p className="font-medium text-sm">{ch.title || `Reto ${ch.number || ch.id}`}</p>
                  <p className="text-xs text-gray-400">{ch.photo_count || 0}/3 fotos</p>
                </div>
                <div className="flex gap-2">
                  {ch.photo_count >= 3 && (
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

  useEffect(() => {
    api('/api/gallery?offset=0&limit=50')
      .then((data) => setPhotos(data.items || data.photos || data || []))
      .catch(() => {});
  }, []);

  const handleDelete = async (id) => {
    if (!confirm('¿Eliminar esta foto?')) return;
    try {
      await api(`/api/admin/gallery/${id}`, { method: 'DELETE' });
      setPhotos((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {photos.map((photo, idx) => (
        <div key={photo.id || idx} className="bg-white rounded-xl overflow-hidden shadow-sm">
          <img src={photo.thumbnail_url || photo.url} alt="" className="aspect-square object-cover w-full" />
          <div className="p-2 flex justify-between items-center">
            <span className="text-xs truncate">{photo.user_name || 'Anónimo'}</span>
            <button onClick={() => handleDelete(photo.id)} className="text-xs px-2 py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
          </div>
        </div>
      ))}
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
    api(`/api/admin/tables/${selectedTable}/challenges`)
      .then((challenges) => {
        const withPhotos = challenges.filter((c) => (c.photos || []).length > 0);
        setChallengePhotos(withPhotos);
      })
      .catch(() => {});
  }, [selectedTable]);

  const handleSelectWinner = async (tableId) => {
    try {
      await api('/api/admin/winner', {
        method: 'POST',
        body: JSON.stringify({ table_id: tableId }),
      });
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
            <option key={t.id} value={t.id}>{t.name || `Mesa ${t.number}`}</option>
          ))}
        </select>
      </div>

      {challengePhotos.map((ch) => (
        <div key={ch.id} className="mb-6">
          <h3 className="font-medium text-sm mb-2">{ch.title || `Reto ${ch.number || ch.id}`}</h3>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {(ch.photos || []).map((photo, idx) => (
              <img
                key={photo.id || idx}
                src={photo.thumbnail_url}
                alt=""
                className="aspect-square object-cover rounded-lg"
              />
            ))}
          </div>
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

export default function AdminPage() {
  const { isAdmin } = useAuth();

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <p className="text-red-500">Acceso no autorizado</p>
      </div>
    );
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
