import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE } from '../api';

const Skeleton = () => (
  <div className="rounded-xl overflow-hidden shadow-sm">
    <div className="skeleton aspect-square" />
    <div className="p-2 space-y-1">
      <div className="skeleton h-3 w-3/4 rounded" />
      <div className="skeleton h-2 w-1/2 rounded" />
    </div>
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

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {photos.map((photo, idx) => (
          <div key={photo.id || idx} className="rounded-xl overflow-hidden shadow-sm bg-white photo-enter">
            <img
              src={thumbnailUrl(photo.thumbnail_path)}
              alt="Foto"
              className="aspect-square object-cover w-full"
              loading="lazy"
            />
            <div className="p-2 space-y-1">
              <div className="flex items-center gap-2">
                {photo.user_google_photo && (
                  <img src={photo.user_google_photo} alt="" className="w-5 h-5 rounded-full object-cover" />
                )}
                <span className="text-xs font-medium truncate">
                  {photo.user_google_name || photo.user_alias || 'Anónimo'}
                </span>
              </div>
              {photo.message && (
                <p className="text-xs text-gray-500 truncate">{photo.message}</p>
              )}
              <a
                href={`${API_BASE}/api/gallery/${photo.id}/download`}
                download
                className="text-xs text-[var(--color-accent)] hover:underline inline-block"
              >
                Descargar
              </a>
            </div>
          </div>
        ))}
      </div>
      {loadingMore && (
        <div className="flex justify-center py-6">
          <span className="spinner spinner-lg" />
        </div>
      )}
      <div ref={sentinelRef} className="h-4" />
    </div>
  );
}
