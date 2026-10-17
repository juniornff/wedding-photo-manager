import { useState, useEffect } from 'react';
import { api } from '../api';
import { photoSrc, photoUrl, authorName } from '../utils';
import PhotoLightbox from './PhotoLightbox';

export default function ChallengePhotosModal({ challenge, onClose, onDeleted }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    api(`/api/admin/challenges/${challenge.id}/photos`)
      .then(setPhotos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [challenge.id]);

  const handleDelete = async (photo) => {
    if (!confirm('¿Eliminar esta foto?')) return;
    try {
      await api(`/api/admin/challenges/${challenge.id}/photos/${photo.id}`, { method: 'DELETE' });
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id));
      setSelectedId((cur) => (cur === photo.id ? null : cur));
      if (onDeleted) onDeleted();
    } catch (err) {
      alert(err.message);
    }
  };

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
                  <button onClick={() => setSelectedId(photo.id)} className="w-full cursor-pointer border-0 p-0">
                    <img
                      src={photoSrc(photo)}
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
                      <span className="text-[11px] truncate">{authorName(photo)}</span>
                    </div>
                    <div className="flex gap-1">
                      <a
                        href={photoUrl(photo.path)}
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

      {selectedId !== null && photos.some((p) => p.id === selectedId) && (
        <PhotoLightbox
          photos={photos}
          index={photos.findIndex((p) => p.id === selectedId)}
          onClose={() => setSelectedId(null)}
          onNavigate={(i) => setSelectedId(photos[i]?.id ?? null)}
          onDelete={handleDelete}
        />
      )}
    </>
  );
}