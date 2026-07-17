import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import PhotoUpload from '../components/PhotoUpload';
import { useAuth } from '../context/AuthContext';
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

  useEffect(() => {
    api(`/api/secret-photographer/table/${qr_code}`)
      .then((data) => {
        setTable(data.table || data);
        setChallenges(data.challenges || []);
      })
      .catch((err) => setError(err.message));
  }, [qr_code]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-500 text-lg mb-2">{error}</p>
          <a href="/" className="text-sm text-[var(--color-accent)] hover:underline">Volver al inicio</a>
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

            <div className="grid grid-cols-3 gap-2 mb-4">
              {(selectedChallenge.photos || []).map((photo, idx) => (
                <img
                  key={photo.id || idx}
                  src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : photo.path ? `${API_BASE}/api/uploads/${photo.path}` : ''}
                  alt=""
                  className="aspect-square object-cover rounded-lg"
                />
              ))}
            </div>

            {!isBlocked(selectedChallenge) && user && (
              <PhotoUpload
                uploadUrl={`/api/secret-photographer/upload?challenge_id=${selectedChallenge.id}`}
                onSuccess={() => {
                  api(`/api/secret-photographer/table/${qr_code}`)
                    .then((data) => {
                      setChallenges(data.challenges || []);
                      const updated = (data.challenges || []).find((c) => c.id === selectedChallenge.id);
                      if (updated) setSelectedChallenge(updated);
                    });
                }}
              />
            )}

            {isBlocked(selectedChallenge) && (
              <p className="text-sm text-red-500 text-center">Este reto está completo</p>
            )}

            {!user && (
              <p className="text-sm text-gray-400 text-center">Inicia sesión para subir fotos</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
