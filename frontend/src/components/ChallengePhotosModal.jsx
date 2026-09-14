import { useState, useEffect } from 'react';
import { api, API_BASE } from '../api';

export default function ChallengePhotosModal({ challenge, onClose, onDeleted }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(null);

  useEffect(() => {
    api(`/api/admin/challenges/${challenge.id}/photos`)
      .then(setPhotos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [challenge.id]);

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

  const handleDelete = async (photo) => {
    if (!confirm('¿Eliminar esta foto?')) return;
    try {
      await api(`/api/admin/challenges/${challenge.id}/photos/${photo.id}`, { method: 'DELETE' });
      const idx = photos.findIndex((p) => p.id === photo.id);
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id));
      if (idx !== -1 && selectedIdx === idx) setSelectedIdx(null);
      if (onDeleted) onDeleted();
    } catch (err) {
      alert(err.message);
    }
  };

  const selected = selectedIdx !== null ? photos[selectedIdx] : null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-2xl p-6 w-full max-w-3xl max-h-[85vh] flex flex-col shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="min-w-0">
              <h2 className="text-lg font-semibold truncate">{challenge.description || `Reto ${challenge.id}`}</h2>
              <p className="text-xs text-gray-400">Fotos subidas a este reto</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl cursor-pointer">
              ×
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <span className="spinner spinner-lg" />
            </div>
          ) : photos.length === 0 ? (
            <p className="text-center text-gray-400 py-12">No hay fotos en este reto</p>
          ) : (
            <div className="overflow-y-auto pr-1 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {photos.map((photo, idx) => (
                <div key={photo.id || idx} className="bg-gray-50 rounded-lg overflow-hidden border border-gray-100">
                  <button onClick={() => setSelectedIdx(idx)} className="w-full cursor-pointer border-0 p-0">
                    <img
                      src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : `${API_BASE}/api/uploads/${photo.path}`}
                      alt=""
                      className="aspect-square object-cover w-full"
                      loading="lazy"
                    />
                  </button>
                  <div className="p-2 space-y-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {photo.user_google_photo && (
                        <img src={photo.user_google_photo} alt="" className="w-4 h-4 rounded-full object-cover shrink-0" />
                      )}
                      <span className="text-[11px] truncate">{photo.user_google_name || photo.user_alias || 'Anónimo'}</span>
                    </div>
                    <div className="flex gap-1">
                      <a
                        href={`${API_BASE}/api/uploads/${photo.path}`}
                        download
                        className="flex-1 text-center text-[11px] py-1 bg-gray-100 rounded cursor-pointer"
                      >
                        Descargar
                      </a>
                      <button
                        onClick={() => handleDelete(photo)}
                        className="flex-1 text-[11px] py-1 bg-red-100 text-red-600 rounded cursor-pointer"
                      >
                        Eliminar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedIdx(null)}
        >
          <div className="relative max-w-3xl w-full max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-end mb-2">
              <button onClick={() => setSelectedIdx(null)} className="text-white text-2xl hover:opacity-70 cursor-pointer">
                &times;
              </button>
            </div>

            <div className="relative flex items-center justify-center bg-black/40 rounded-t-xl overflow-hidden min-h-[250px]">
              {selectedIdx > 0 && (
                <button
                  onClick={() => setSelectedIdx(selectedIdx - 1)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2"
                >
                  ‹
                </button>
              )}
              <img
                src={`${API_BASE}/api/uploads/${selected.path}`}
                alt="Foto del reto"
                className="max-w-full max-h-[70vh] object-contain"
              />
              {selectedIdx < photos.length - 1 && (
                <button
                  onClick={() => setSelectedIdx(selectedIdx + 1)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2"
                >
                  ›
                </button>
              )}
            </div>

            <div className="bg-white rounded-b-xl p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 min-w-0">
                {selected.user_google_photo && (
                  <img src={selected.user_google_photo} alt="" className="w-6 h-6 rounded-full object-cover shrink-0" />
                )}
                <div className="min-w-0">
                  <span className="text-sm font-medium truncate block">
                    {selected.user_google_name || selected.user_alias || 'Anónimo'}
                  </span>
                  {selected.message && (
                    <span className="text-xs text-gray-500 truncate block">{selected.message}</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <a
                  href={`${API_BASE}/api/uploads/${selected.path}`}
                  download
                  className="text-sm px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer"
                >
                  Descargar
                </a>
                <button
                  onClick={() => handleDelete(selected)}
                  className="text-sm px-4 py-2 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 transition cursor-pointer"
                >
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}