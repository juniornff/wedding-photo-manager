import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE } from '../api';
import { thumbnailUrl } from '../utils';
import PhotoLightbox from './PhotoLightbox';

const Skeleton = () => (
  <div className="rounded-xl overflow-hidden shadow-sm">
    <div className="skeleton aspect-square" />
  </div>
);

export default function PhotoGrid({ fetchUrl, emptyMessage = 'No hay fotos aún' }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const sentinelRef = useRef(null);
  const requestIdRef = useRef(0);

  const fetchPhotos = useCallback(async (currentOffset, append = false) => {
    const requestId = ++requestIdRef.current;
    if (!append) setLoading(true);
    else setLoadingMore(true);
    try {
      const url = `${fetchUrl}${fetchUrl.includes('?') ? '&' : '?'}offset=${currentOffset}&limit=12`;
      const res = await fetch(`${API_BASE}${url}`);
      if (!res.ok) throw new Error('Error al cargar fotos');
      const data = await res.json();
      if (requestId !== requestIdRef.current) return;
      const items = Array.isArray(data) ? data : (data.items || data.photos || []);
      if (append) {
        setPhotos((prev) => [...prev, ...items]);
      } else {
        setPhotos(items);
      }
      setOffset(currentOffset + items.length);
      if (items.length < 12) setHasMore(false);
    } catch {
      if (requestId === requestIdRef.current) setHasMore(false);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [fetchUrl]);

  useEffect(() => {
    fetchPhotos(0, false);
  }, [fetchPhotos]);

  useEffect(() => {
    let timer = null;
    const handler = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        setHasMore(true);
        fetchPhotos(0, false);
      }, 250);
    };
    window.addEventListener('refresh-gallery', handler);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('refresh-gallery', handler);
    };
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

      {selectedIdx !== null && (
        <PhotoLightbox
          photos={photos}
          index={selectedIdx}
          onClose={() => setSelectedIdx(null)}
          onNavigate={setSelectedIdx}
        />
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
