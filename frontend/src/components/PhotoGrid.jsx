import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE } from '../api';

const Skeleton = () => (
  <div className="rounded-xl overflow-hidden shadow-sm">
    <div className="skeleton aspect-square" />
  </div>
);

function photoUrl(path) {
  return `${API_BASE}/api/uploads/${path}`;
}

function thumbnailUrl(path) {
  return `${API_BASE}/api/thumbnails/${path}`;
}

export default function PhotoGrid({ fetchUrl, emptyMessage = 'No hay fotos aún' }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const sentinelRef = useRef(null);

  const fetchPhotos = useCallback(async (currentOffset, append = false) => {
    if (!append) setLoading(true);
    else setLoadingMore(true);
    try {
      const url = `${fetchUrl}${fetchUrl.includes('?') ? '&' : '?'}offset=${currentOffset}&limit=12`;
      const res = await fetch(`${API_BASE}${url}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.photos || []);
      if (append) {
        setPhotos((prev) => [...prev, ...items]);
      } else {
        setPhotos(items);
      }
      setOffset(currentOffset + items.length);
      if (items.length < 12) setHasMore(false);
    } catch {
      setHasMore(false);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [fetchUrl]);

  useEffect(() => {
    fetchPhotos(0, false);
  }, [fetchPhotos]);

  useEffect(() => {
    const handler = () => {
      setHasMore(true);
      fetchPhotos(0, false);
    };
    window.addEventListener('refresh-gallery', handler);
    return () => window.removeEventListener('refresh-gallery', handler);
  }, [fetchPhotos]);

  useEffect(() => {
    if (!sentinelRef.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore && !loadingMore && !loading) {
          fetchPhotos(offset, true);
        }
      },
      { rootMargin: '200px' }
    );
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [fetchPhotos, offset, hasMore, loadingMore, loading]);

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

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );
  }

  if (photos.length === 0) {
    return <p className="text-center text-gray-400 py-12">{emptyMessage}</p>;
  }

  const selected = selectedIdx !== null ? photos[selectedIdx] : null;

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {photos.map((photo, idx) => (
          <button
            key={photo.id || idx}
            onClick={() => setSelectedIdx(idx)}
            className="rounded-xl overflow-hidden shadow-sm bg-white photo-enter cursor-pointer text-left p-0 border-0"
          >
            <img
              src={thumbnailUrl(photo.thumbnail_path)}
              alt={photo.message || 'Foto'}
              className="aspect-square object-cover w-full"
              loading="lazy"
            />
          </button>
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
            <button
              onClick={() => setSelectedIdx(null)}
              className="absolute -top-10 right-0 text-white text-2xl hover:opacity-70 cursor-pointer z-10"
            >
              &times;
            </button>

            <div className="relative flex items-center justify-center bg-black/40 rounded-t-xl overflow-hidden min-h-[300px]">
              {selectedIdx > 0 && (
                <button
                  onClick={() => setSelectedIdx(selectedIdx - 1)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 text-white text-4xl hover:opacity-70 cursor-pointer z-10 px-2"
                >
                  ‹
                </button>
              )}
              <img
                src={photoUrl(selected.path)}
                alt={selected.message || 'Foto'}
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
                <span className="text-sm font-medium truncate">
                  {selected.user_google_name || selected.user_alias || 'Anónimo'}
                </span>
                {selected.message && (
                  <span className="text-sm text-gray-500 truncate">&mdash; {selected.message}</span>
                )}
              </div>
              <a
                href={`${API_BASE}/api/gallery/${selected.id}/download`}
                download
                className="shrink-0 text-sm px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer"
              >
                Descargar
              </a>
            </div>
          </div>
        </div>
      )}

      {loadingMore && (
        <div className="flex justify-center py-6">
          <span className="spinner spinner-lg" />
        </div>
      )}
      <div ref={sentinelRef} className="h-4" />
    </div>
  );
}
