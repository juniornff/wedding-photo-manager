import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/useAuth';
import { api, apiUpload, API_BASE } from '../api';
import ChallengePhotosModal from '../components/ChallengePhotosModal';

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

const DEFAULT_COLORS = {
  color_primary: '#e8a0b4',
  color_secondary: '#f5d6c6',
  color_accent: '#c48b9d',
  color_bg: '#fdf6f0',
  color_text: '#4a3728',
};

const COLOR_FIELDS = [
  { key: 'color_primary', label: 'Principal', desc: 'Botones, títulos, pestañas activas' },
  { key: 'color_secondary', label: 'Secundario', desc: 'Fondos de secciones, bordes' },
  { key: 'color_accent', label: 'Terciario', desc: 'Enlaces y detalles decorativos' },
  { key: 'color_bg', label: 'Fondo página', desc: 'Color de fondo general del sitio' },
  { key: 'color_text', label: 'Texto', desc: 'Color del texto principal' },
];

function ColorField({ label, desc, value, onChange, defaultVal }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <div className="w-24 shrink-0">
          <label className="text-sm font-medium">{label}</label>
          <p className="text-[10px] text-gray-400 leading-tight">{desc}</p>
        </div>
        <input
          type="color"
          value={value || defaultVal || '#000000'}
          onChange={(e) => onChange(e.target.value)}
          className="w-10 h-10 rounded cursor-pointer border-0 p-0.5 shrink-0"
        />
        <input
          type="text"
          value={value || defaultVal || ''}
          onChange={(e) => onChange(e.target.value)}
          className="border rounded-lg p-2 text-sm font-mono flex-1"
          placeholder={defaultVal || '#000000'}
          maxLength={7}
        />
      </div>
    </div>
  );
}

function WeddingInfoTab() {
  const [form, setForm] = useState({ novio1_name: '', novio2_name: '', wedding_date: '', color_primary: '', color_secondary: '', color_accent: '', color_bg: '', color_text: '', carousel_interval: 5 });
  const [msg, setMsg] = useState('');

  const initForm = (data) => {
    const colors = (data?.color_scheme || '').split(',').map((c) => c.trim());
    setForm({
      novio1_name: data?.novio1_name || '',
      novio2_name: data?.novio2_name || '',
      wedding_date: data?.wedding_date || '',
      color_primary: colors[0] || '',
      color_secondary: colors[1] || '',
      color_accent: colors[2] || '',
      color_bg: colors[3] || '',
      color_text: colors[4] || '',
      carousel_interval: data?.carousel_interval ?? 5,
    });
  };

  useEffect(() => {
    api('/api/wedding-info').then(initForm).catch(() => {});
  }, []);

  const handleSave = async () => {
    try {
      const parts = COLOR_FIELDS.map((f) => form[f.key] || DEFAULT_COLORS[f.key]).filter(Boolean);
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

  const handleReset = () => {
    setForm((prev) => ({
      ...prev,
      ...Object.fromEntries(COLOR_FIELDS.map((f) => [f.key, ''])),
    }));
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
      <div className="space-y-4 pt-2 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold">Esquema de color</p>
          <button onClick={handleReset} className="text-xs px-3 py-1 rounded border border-gray-300 text-gray-500 hover:bg-gray-100 cursor-pointer">Restaurar valores iniciales</button>
        </div>
        {COLOR_FIELDS.map((f) => (
          <ColorField key={f.key} label={f.label} desc={f.desc} value={form[f.key]} defaultVal={DEFAULT_COLORS[f.key]} onChange={(v) => setForm({ ...form, [f.key]: v })} />
        ))}
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Intervalo del carrusel (segundos)</label>
        <input type="number" min="2" max="60" value={form.carousel_interval} onChange={(e) => setForm({ ...form, carousel_interval: parseInt(e.target.value) || 5 })} className="w-full border rounded-lg p-2 text-sm" />
      </div>
      <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm cursor-pointer">Salvar</button>
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
  const [qrModal, setQrModal] = useState(null);

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
      <div className="space-y-3">
        {tables.map((table) => (
          <div key={table.id} className="bg-white rounded-lg p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-sm">{table.name || `Mesa ${table.number}`}</p>
                <p className="text-xs text-gray-400">QR: {table.qr_code}</p>
              </div>
              <div className="flex gap-2">
                {table.qr_url && (
                  <button
                    onClick={() => setQrModal(table)}
                    className="text-xs px-3 py-1 bg-gray-100 rounded cursor-pointer"
                  >
                    QR
                  </button>
                )}
                <button
                  onClick={() => {
                    const url = `${window.location.origin}/fotografo-secreto/${table.qr_code}`;
                    navigator.clipboard.writeText(url);
                  }}
                  className="text-xs px-3 py-1 bg-blue-100 text-blue-600 rounded cursor-pointer"
                >Copiar URL</button>
                <button onClick={() => handleDelete(table.id)} className="text-xs px-3 py-1 bg-red-100 text-red-600 rounded cursor-pointer">Eliminar</button>
              </div>
            </div>
            {table.participants && table.participants.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-1">Participantes ({table.participants.length}):</p>
                <div className="flex flex-wrap gap-2">
                  {table.participants.map((p) => (
                    <span key={p.id} className="flex items-center gap-1 text-xs bg-gray-50 rounded-full px-2 py-1">
                      {p.google_photo && (
                        <img src={p.google_photo} alt="" className="w-4 h-4 rounded-full" />
                      )}
                      {p.google_name || p.alias}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {qrModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setQrModal(null)}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <div className="min-w-0">
                <h2 className="text-lg font-semibold truncate">{qrModal.name || `Mesa ${qrModal.number || qrModal.id}`}</h2>
                <p className="text-xs text-gray-400">Código QR de la mesa</p>
              </div>
              <button
                onClick={() => setQrModal(null)}
                className="text-gray-400 hover:text-gray-600 text-xl cursor-pointer"
              >
                ×
              </button>
            </div>

            {qrModal.qr_url && (
              <img
                src={`${API_BASE}${qrModal.qr_url}`}
                alt={`QR de ${qrModal.name || qrModal.id}`}
                className="w-full max-w-[220px] mx-auto rounded-lg"
              />
            )}

            <p className="text-xs text-gray-500 text-center mt-4 break-all">
              {`${window.location.origin}/fotografo-secreto/${qrModal.qr_code}`}
            </p>

            <div className="flex justify-center gap-2 mt-4">
              {qrModal.qr_url && (
                <a
                  href={`${API_BASE}${qrModal.qr_url}`}
                  download
                  className="text-xs px-3 py-1 bg-gray-100 rounded cursor-pointer"
                >
                  Descargar QR
                </a>
              )}
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/fotografo-secreto/${qrModal.qr_code}`);
                }}
                className="text-xs px-3 py-1 bg-blue-100 text-blue-600 rounded cursor-pointer"
              >
                Copiar URL
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ChallengesTab() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [newTitle, setNewTitle] = useState('');
  const [manageChallenge, setManageChallenge] = useState(null);

  useEffect(() => {
    api('/api/admin/tables').then(setTables).catch(() => {});
  }, []);

  const loadChallenges = useCallback(() => {
    if (!selectedTable) return;
    api(`/api/admin/challenges?table_id=${selectedTable}`)
      .then(setChallenges)
      .catch(() => {});
  }, [selectedTable]);

  useEffect(() => {
    loadChallenges();
  }, [loadChallenges]);

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
                  <button
                    onClick={() => setManageChallenge(ch)}
                    className="text-xs px-3 py-1 bg-green-100 text-green-700 rounded cursor-pointer"
                  >
                    Fotos
                  </button>
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

      {manageChallenge && (
        <ChallengePhotosModal
          challenge={manageChallenge}
          onClose={() => setManageChallenge(null)}
          onDeleted={loadChallenges}
        />
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

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [tables, setTables] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [draftAlias, setDraftAlias] = useState('');
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async () => {
    try {
      const [u, t] = await Promise.all([api('/api/admin/users'), api('/api/admin/tables')]);
      setUsers(u);
      setTables(t);
    } catch (err) {
      alert(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRename = async (user) => {
    const alias = draftAlias.trim();
    if (!alias || alias === user.alias) {
      setEditingId(null);
      return;
    }
    try {
      await api(`/api/admin/users/${user.id}`, {
        method: 'PUT',
        body: JSON.stringify({ alias }),
      });
      await load();
      setEditingId(null);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleTableChange = async (user, value) => {
    try {
      await api(`/api/admin/users/${user.id}/table`, {
        method: 'PATCH',
        body: JSON.stringify({ table_id: value === '' ? null : Number(value) }),
      });
      await load();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (deletePhotos) => {
    const user = deleting;
    setDeleting(null);
    try {
      await api(`/api/admin/users/${user.id}?delete_photos=${deletePhotos}`, {
        method: 'DELETE',
      });
      await load();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <p className="text-sm text-gray-500 mb-3">{users.length} usuarios registrados</p>
      {users.length === 0 ? (
        <p className="text-gray-400">Sin usuarios registrados.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-200">
                <th className="py-2 pr-3">Usuario</th>
                <th className="py-2 pr-3">Mesa</th>
                <th className="py-2 pr-3">Fotos</th>
                <th className="py-2 pr-3">Fecha</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-100">
                  <td className="py-2 pr-3">
                    {editingId === u.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          value={draftAlias}
                          onChange={(e) => setDraftAlias(e.target.value)}
                          className="border rounded px-2 py-1 text-sm w-40"
                          autoFocus
                        />
                        <button
                          onClick={() => handleRename(u)}
                          className="text-xs px-2 py-1 bg-[var(--color-primary)] text-white rounded cursor-pointer"
                        >
                          Guardar
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-xs px-2 py-1 bg-gray-100 rounded cursor-pointer"
                        >
                          ×
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        {u.google_photo && (
                          <img src={u.google_photo} alt="" className="w-6 h-6 rounded-full" />
                        )}
                        <div>
                          <p className="font-medium">
                            {u.google_name || u.alias}
                            {u.role === 'admin' ? (
                              <span className="ml-2 inline-block text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium align-middle">
                                Admin
                              </span>
                            ) : (
                              <span className="ml-2 inline-block text-[10px] px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-600 font-medium align-middle">
                                Invitado
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-gray-400">
                            {u.email}
                            {u.google_auth && <span className="ml-1 text-blue-500">• Google</span>}
                          </p>
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="py-2 pr-3">
                    <select
                      value={u.table_id ?? ''}
                      onChange={(e) => handleTableChange(u, e.target.value)}
                      className="border rounded px-2 py-1 text-sm bg-white"
                    >
                      <option value="">Sin mesa</option>
                      {tables.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name || `Mesa ${t.number}`}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 pr-3 text-gray-500">
                    {(u.gallery_count || 0) + (u.challenge_count || 0)}
                  </td>
                  <td className="py-2 pr-3 text-gray-400 text-xs">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="py-2">
                    {editingId !== u.id && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            setEditingId(u.id);
                            setDraftAlias(u.alias);
                          }}
                          className="text-xs px-2 py-1 bg-gray-100 rounded cursor-pointer"
                        >
                          Renombrar
                        </button>
                        <button
                          onClick={() => setDeleting(u)}
                          className="text-xs px-2 py-1 bg-red-100 text-red-600 rounded cursor-pointer"
                        >
                          Eliminar
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deleting && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-1">Eliminar usuario</h3>
            <p className="text-sm text-gray-500 mb-4">
              {deleting.google_name || deleting.alias || 'Anónimo'} —{' '}
              {(deleting.gallery_count || 0) + (deleting.challenge_count || 0)} fotos
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => handleDelete(false)}
                className="text-sm px-3 py-2 bg-gray-100 rounded cursor-pointer text-left"
              >
                Conservar sus fotos (quedarán anónimas)
              </button>
              <button
                onClick={() => handleDelete(true)}
                className="text-sm px-3 py-2 bg-red-600 text-white rounded cursor-pointer text-left"
              >
                Eliminar también sus fotos
              </button>
              <button
                onClick={() => setDeleting(null)}
                className="text-sm px-3 py-2 bg-gray-100 rounded cursor-pointer"
              >
                Cancelar
              </button>
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
  const [currentWinner, setCurrentWinner] = useState(null);

  const loadWinner = useCallback(() => {
    api('/api/wedding-info').then(setCurrentWinner).catch(() => {});
  }, []);

  useEffect(() => {
    api('/api/admin/tables').then(setTables).catch(() => {});
    loadWinner();
  }, [loadWinner]);

  useEffect(() => {
    if (!selectedTable) return;
    api(`/api/admin/tables/${selectedTable}/photos`)
      .then((data) => setChallengePhotos(data || []))
      .catch(() => {});
  }, [selectedTable]);

  const handleSelectWinner = async (tableId) => {
    try {
      await api(`/api/admin/select-winner?table_id=${tableId}`, { method: 'POST' });
      loadWinner();
      alert('¡Ganador seleccionado!');
    } catch (err) {
      alert(err.message);
    }
  };

  const handleClearWinner = async () => {
    if (!confirm('¿Quitar el ganador actual?')) return;
    try {
      await api('/api/admin/select-winner', { method: 'DELETE' });
      loadWinner();
      alert('Ganador deseleccionado.');
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

      {currentWinner?.winner_table_id && (
        <div className="mt-8 p-4 rounded-xl border-2 border-yellow-300 bg-yellow-50 flex items-center justify-between gap-4">
          <p className="text-sm font-semibold text-yellow-800">
            🏆 Ganador actual: {currentWinner.winner_table_name || `Mesa ${currentWinner.winner_table_id}`}
          </p>
          <button
            onClick={handleClearWinner}
            className="px-4 py-2 rounded-lg bg-red-100 text-red-600 text-sm hover:bg-red-200 transition cursor-pointer shrink-0"
          >
            Quitar ganador
          </button>
        </div>
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
  const [tab, setTab] = useState('dashboard');

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

  const tabs = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'info', label: 'Info Boda' },
    { key: 'carousel', label: 'Carrusel' },
    { key: 'tables', label: 'Mesas' },
    { key: 'challenges', label: 'Retos' },
    { key: 'gallery', label: 'Galería' },
    { key: 'users', label: 'Usuarios' },
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
        {tab === 'users' && <UsersTab />}
        {tab === 'winner' && <WinnerTab />}
      </div>
    </div>
  );
}
