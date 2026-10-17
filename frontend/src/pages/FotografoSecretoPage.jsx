import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import PhotoUpload from '../components/PhotoUpload';
import PhotoLightbox from '../components/PhotoLightbox';
import { useAuth } from '../context/useAuth';
import { api, API_BASE } from '../api';

function isBlocked(ch) {
  return ch.photo_count >= ch.max_photos && ch.max_photos > 0 && !ch.locked;
}

function isComplete(ch) {
  return ch.photo_count >= ch.max_photos && ch.max_photos > 0;
}

export default function FotografoSecretoPage() {
  const { qr_code } = useParams();
  const { user } = useAuth();
  const [table, setTable] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [error, setError] = useState(null);
  const [selectedChallenge, setSelectedChallenge] = useState(null);
  const [viewingMyPhoto, setViewingMyPhoto] = useState(false);

  const fetchTable = useCallback(async () => {
    const query = user ? `?user_id=${user.id}` : '';
    return api(`/api/secret-photographer/table/${qr_code}${query}`);
  }, [qr_code, user]);

  const loadTable = useCallback(() => {
    fetchTable()
      .then((data) => {
        setTable(data.table || data);
        setChallenges(data.challenges || []);
        setError(null);
        if (user) {
          window.dispatchEvent(new CustomEvent('table-assigned'));
        }
      })
      .catch((err) => setError(err.message));
  }, [fetchTable, user]);

  useEffect(() => {
    loadTable();
  }, [loadTable]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-500 text-lg mb-3">{error}</p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => {
                setError(null);
                setTable(null);
                loadTable();
              }}
              className="text-sm px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer"
            >
              Reintentar
            </button>
            <Link to="/" className="text-sm text-[var(--color-accent)] hover:underline">Volver al inicio</Link>
          </div>
        </div>
      </div>
    );
  }

  if (!table) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">{table.name || `Mesa ${table.number || ''}`}</h1>
      <p className="text-sm text-gray-500 mb-6">Fotógrafo Secreto — Completa los retos</p>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {challenges.map((challenge) => (
          <button
            key={challenge.id}
            onClick={() => setSelectedChallenge(challenge)}
            className={`rounded-xl p-4 text-center border-2 transition cursor-pointer ${
              isBlocked(challenge)
                ? 'border-red-300 bg-red-50 opacity-60'
                : isComplete(challenge)
                ? 'border-green-300 bg-green-50'
                : challenge.photo_count > 0
                ? 'border-green-200 bg-green-50'
                : 'border-gray-200 bg-white hover:border-[var(--color-primary)]'
            }`}
          >
            <p className="text-xs font-semibold truncate">{challenge.description || `Reto ${challenge.id}`}</p>
            <p className="text-xs text-gray-400 mt-1">{challenge.photo_count || 0}/{challenge.max_photos || 0} fotos</p>
            {challenge.my_photo && (
              <span className="mt-1 inline-block text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                ✓ Tu foto subida
              </span>
            )}
          </button>
        ))}
      </div>

      {selectedChallenge && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedChallenge(null)}>
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-semibold">{selectedChallenge.description || 'Reto'}</h2>
              <button
                onClick={() => setSelectedChallenge(null)}
                className="text-gray-400 hover:text-gray-600 text-xl cursor-pointer"
              >
                ×
              </button>
            </div>

            {selectedChallenge.description && (
              <p className="text-sm text-gray-600 mb-4">{selectedChallenge.description}</p>
            )}

            {selectedChallenge.my_photo ? (
              <>
                <div className="flex justify-center mb-3">
                  <button onClick={() => setViewingMyPhoto(true)} className="cursor-pointer group">
                    <img
                      src={
                        selectedChallenge.my_photo.thumbnail_path
                          ? `${API_BASE}/api/thumbnails/${selectedChallenge.my_photo.thumbnail_path}`
                          : `${API_BASE}/api/uploads/${selectedChallenge.my_photo.path}`
                      }
                      alt="Tu foto"
                      className="max-h-72 rounded-xl object-contain group-hover:opacity-90 transition"
                    />
                  </button>
                </div>
                {selectedChallenge.my_photo.message && (
                  <p className="text-sm text-gray-600 text-center mb-2 italic">
                    “{selectedChallenge.my_photo.message}”
                  </p>
                )}
                <p className="text-xs text-green-600 text-center mb-2">
                  ✓ Ya subiste tu foto para este reto — clic sobre la foto para verla completa
                </p>
              </>
            ) : isBlocked(selectedChallenge) ? (
              <p className="text-sm text-red-500 text-center mb-4">Este reto está completo</p>
            ) : !user ? (
              <p className="text-sm text-gray-400 text-center mb-4">Inicia sesión para subir fotos</p>
            ) : (
              <>
                <p className="text-sm text-gray-400 text-center mb-3">
                  Aún no subes tu foto para este reto
                </p>
                <PhotoUpload
                  uploadUrl={`/api/secret-photographer/upload?challenge_id=${selectedChallenge.id}`}
                  onSuccess={() => {
                    fetchTable()
                      .then((data) => {
                        setChallenges(data.challenges || []);
                        const updated = (data.challenges || []).find((c) => c.id === selectedChallenge.id);
                        if (updated) setSelectedChallenge(updated);
                      })
                      .catch((err) => setError(err.message));
                  }}
                />
              </>
            )}

            {viewingMyPhoto && selectedChallenge.my_photo && (
              <PhotoLightbox
                photos={[selectedChallenge.my_photo]}
                index={0}
                onClose={() => setViewingMyPhoto(false)}
                onNavigate={() => {}}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
