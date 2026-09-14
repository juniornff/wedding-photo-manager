import { useState, useEffect, useRef, useCallback } from 'react';
import PhotoLightbox from '../components/PhotoLightbox';
import { API_BASE, api } from '../api';

const CONFETTI_COLORS = ['#ffd700', '#e8a0b4', '#f5d6c6', '#c48b9d', '#f4a261', '#94d2bd'];

function Confetti() {
  const pieces = Array.from({ length: 28 }, () => ({
    left: Math.random() * 100,
    delay: Math.random() * 1.2,
    duration: 2.4 + Math.random() * 1.6,
    color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
    size: 6 + Math.random() * 6,
  }));

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-[70]" aria-hidden>
      {pieces.map((p, i) => (
        <span
          key={i}
          className="confetti"
          style={{
            left: `${p.left}%`,
            width: `${p.size}px`,
            height: `${p.size * 0.5}px`,
            backgroundColor: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
          }}
        />
      ))}
    </div>
  );
}

function ProgressBar({ current, max }) {
  const pct = max > 0 ? Math.min(100, Math.round((current / max) * 100)) : 0;
  return (
    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
      <div className="h-full bg-[var(--color-primary)] rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

function authorChip(photo) {
  const name = photo.user_google_name || photo.user_alias || 'Anónimo';
  return (
    <span className="absolute bottom-1 left-1 flex items-center gap-1 bg-black/60 text-white text-[10px] rounded-full px-1.5 py-0.5 max-w-[calc(100%-8px)]">
      {photo.user_google_photo && (
        <img src={photo.user_google_photo} alt="" className="w-3 h-3 rounded-full shrink-0" />
      )}
      <span className="truncate">{name}</span>
    </span>
  );
}

export default function SecretDashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confetti, setConfetti] = useState(false);
  const [lightbox, setLightbox] = useState(null);

  const prevIdsRef = useRef(new Set());
  const newIdsRef = useRef(new Set());
  const prevWinnerRef = useRef(null);
  const debounceRef = useRef(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await api('/api/secret-photographer/dashboard');

      const current = new Set();
      data.tables?.forEach((t) => t.challenges?.forEach((c) => c.photos?.forEach((p) => current.add(p.id))));
      const delta = new Set([...current].filter((id) => !prevIdsRef.current.has(id)));
      prevIdsRef.current = current;
      newIdsRef.current = delta;

      const winner = data.winner_table_id ?? null;
      if (winner && winner !== prevWinnerRef.current) {
        setConfetti(true);
        setTimeout(() => setConfetti(false), 6000);
      }
      prevWinnerRef.current = winner;

      setDashboard(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/events`);
    const reload = () => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(fetchDashboard, 250);
    };
    es.addEventListener('new_challenge_photo', reload);
    es.addEventListener('challenge_photo_deleted', reload);
    es.addEventListener('winner_selected', reload);
    fetchDashboard();
    return () => {
      clearTimeout(debounceRef.current);
      es.close();
    };
  }, [fetchDashboard]);

  const allChallenges = dashboard?.tables?.flatMap((t) => t.challenges ?? []) ?? [];
  const lightboxPhotos = lightbox ? allChallenges.find((c) => c.id === lightbox.challengeId)?.photos ?? [] : [];
  const totalPhotos = dashboard?.tables?.reduce((acc, t) => acc + t.photo_count, 0) ?? 0;
  const totalMax = dashboard?.tables?.reduce((acc, t) => acc + t.max_photos, 0) ?? 0;
  const isComplete = (ch) => ch.max_photos > 0 && ch.photo_count >= ch.max_photos;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="spinner spinner-lg" />
      </div>
    );
  }

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

  return (
    <div className="min-h-screen max-w-7xl mx-auto px-4 py-8">
      {confetti && <Confetti />}

      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-1">Fotógrafo Secreto</h1>
        <p className="text-sm text-gray-500">Tablero del reto en vivo — los invitados ven cómo avanza cada mesa</p>
        <div className="mt-3 inline-flex items-center gap-2 text-sm bg-white border border-gray-100 rounded-full px-4 py-1.5 shadow-sm">
          <span className="font-semibold">{totalPhotos}</span>
          <span className="text-gray-400">/</span>
          <span>{totalMax}</span>
          <span className="text-gray-500">fotos subidas</span>
        </div>
      </div>

      {dashboard?.winner_table_name && (
        <div className="winner-pop mb-8 rounded-2xl bg-gradient-to-r from-yellow-100 via-amber-100 to-yellow-100 border-2 border-yellow-400 p-5 text-center shadow-md">
          <span className="text-4xl mr-3">👑</span>
          <span className="text-2xl font-bold text-yellow-800">
            ¡Mesa ganadora: {dashboard.winner_table_name}!
          </span>
          <span className="text-4xl ml-3">🎉</span>
        </div>
      )}

      {(!dashboard?.tables || dashboard.tables.length === 0) ? (
        <p className="text-center text-gray-400 py-16">
          Todavía no hay mesas creadas. Cuando el admin cree las mesas y los retos, aparecerán aquí.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboard.tables.map((table) => {
            const isWinner = table.id === dashboard.winner_table_id;
            const completed = table.challenges.filter(isComplete).length;
            const totalRetos = table.challenges.length;
            return (
              <div
                key={table.id}
                className={`rounded-2xl bg-white border p-5 shadow-sm ${
                  isWinner
                    ? 'border-yellow-400 ring-2 ring-yellow-300 winner-ring'
                    : 'border-gray-100'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    {table.name}
                    {isWinner && <span className="text-xl">👑</span>}
                  </h2>
                  <span className="text-xs text-gray-400">
                    {completed}/{totalRetos} retos
                  </span>
                </div>
                <ProgressBar current={completed} max={totalRetos} />
                <span className="text-[11px] text-gray-400 mt-1 block">
                  {totalRetos > 0
                    ? `${completed} de ${totalRetos} retos completados`
                    : 'Sin retos aún'}
                </span>

                <div className="mt-4 space-y-4">
                  {table.challenges.map((challenge) => {
                    const complete = isComplete(challenge);
                    return (
                      <div key={challenge.id} className="border-t border-gray-100 pt-3">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className="text-sm font-medium truncate">{challenge.description}</p>
                          <span
                            className={`shrink-0 text-[10px] px-2 py-0.5 rounded-full ${
                              complete
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {complete ? `Completo${challenge.locked ? ' 🔒' : ''}` : `${challenge.photo_count}/${challenge.max_photos}`}
                          </span>
                        </div>
                        <ProgressBar current={challenge.photo_count} max={challenge.max_photos} />

                        {challenge.photos.length > 0 && (
                          <div className="mt-2 grid grid-cols-3 sm:grid-cols-4 gap-2">
                            {challenge.photos.map((photo, i) => (
                              <button
                                key={photo.id}
                                onClick={() => setLightbox({ challengeId: challenge.id, index: i })}
                                className={`relative group cursor-pointer ${newIdsRef.current.has(photo.id) ? 'photo-enter' : ''}`}
                              >
                                <img
                                  src={photo.thumbnail_path ? `${API_BASE}/api/thumbnails/${photo.thumbnail_path}` : `${API_BASE}/api/uploads/${photo.path}`}
                                  alt=""
                                  className="aspect-square object-cover w-full rounded-lg group-hover:opacity-90 transition"
                                  loading="lazy"
                                />
                                {authorChip(photo)}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {lightbox && (
        <PhotoLightbox
          photos={lightboxPhotos}
          index={lightbox.index}
          onClose={() => setLightbox(null)}
          onNavigate={(i) => setLightbox({ challengeId: lightbox.challengeId, index: i })}
        />
      )}
    </div>
  );
}