import { useEffect } from 'react';
import { API_BASE } from '../api';

export default function PhotoLightbox({ photos, index, onClose, onNavigate, onDelete }) {
  const selected = photos[index];
  const total = photos.length;

  useEffect(() => {
    if (index === null || index === undefined || !selected) return;
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && index > 0) onNavigate(index - 1);
      if (e.key === 'ArrowRight' && index < total - 1) onNavigate(index + 1);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [index, total, selected, onClose, onNavigate]);

  if (!selected) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60] p-4"
      onClick={onClose}
    >
      <div className="relative max-w-3xl w-full max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-end mb-2">
          <button onClick={onClose} className="text-white text-2xl hover:opacity-70 cursor-pointer">
            &times;
          </button>
        </div>

        <div className="relative flex items-center justify-center bg-black/40 rounded-t-xl overflow-hidden min-h-[250px]">
          {index > 0 && (
            <button
              onClick={() => onNavigate(index - 1)}
              className="absolute left-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2"
            >
              ‹
            </button>
          )}
          <img
            src={`${API_BASE}/api/uploads/${selected.path}`}
            alt="Foto"
            className="max-w-full max-h-[70vh] object-contain"
          />
          {index < total - 1 && (
            <button
              onClick={() => onNavigate(index + 1)}
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
            {onDelete && (
              <button
                onClick={() => onDelete(selected)}
                className="text-sm px-4 py-2 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 transition cursor-pointer"
              >
                Eliminar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}