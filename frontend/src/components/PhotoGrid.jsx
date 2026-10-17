import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE, api } from '../api';
import { thumbnailUrl, downloadZip, downloadIndividuals } from '../utils';
import usePhotoSelection from '../hooks/usePhotoSelection';
import useLongPress from '../hooks/useLongPress';
import PhotoLightbox from './PhotoLightbox';
import SelectionToolbar from './SelectionToolbar';
import DownloadDialog from './DownloadDialog';

const Skeleton = () => (
  <div className="rounded-xl overflow-hidden shadow-sm">
    <div className="skeleton aspect-square" />
  </div>
);

const PAGE_SIZE = 12;
const SELECT_ALL_PAGE_SIZE = 500;

export default function PhotoGrid({ fetchUrl, emptyMessage = 'No hay fotos aún' }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [selectingAll, setSelectingAll] = useState(false);
  const [showDialog, setShowDialog] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const sentinelRef = useRef(null);
  const requestIdRef = useRef(0);
  const selection = usePhotoSelection();
  const lp = useLongPress((id) => {
    selection.enter();
    selection.toggle(id);
  });

  const fetchPhotos = useCallback(async (currentOffset, append = false) => {
    const requestId = ++requestIdRef.current;
    if (!append) setLoading(true);
    else setLoadingMore(true);
    try {
      const url = `${fetchUrl}${fetchUrl.includes('?') ? '&' : '?'}offset=${currentOffset}&limit=${PAGE_SIZE}`;
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
      if (items.length < PAGE_SIZE) setHasMore(false);
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

  const handlePhotoClick = (photo, idx) => {
    if (lp.consumeClick()) return;
    if (selection.selectMode) selection.toggle(photo.id);
    else setSelectedIdx(idx);
  };

  const handleSelectAll = async () => {
    setSelectingAll(true);
    try {
      const allIds = [];
      let currentOffset = 0;
      for (;;) {
        const url = `${fetchUrl}${fetchUrl.includes('?') ? '&' : '?'}offset=${currentOffset}&limit=${SELECT_ALL_PAGE_SIZE}`;
        const data = await api(url);
        const items = Array.isArray(data) ? data : (data.items || data.photos || []);
        allIds.push(...items.map((p) => p.id));
        currentOffset += items.length;
        if (items.length < SELECT_ALL_PAGE_SIZE) break;
      }
      selection.selectAll(allIds);
    } catch {
      selection.selectAll(photos.map((p) => p.id));
    } finally {
      setSelectingAll(false);
    }
  };

  const handleDownload = async (mode) => {
    const ids = [...selection.selectedIds];
    setDownloadError(null);
    setDownloadBusy(mode);
    try {
      if (mode === 'zip') {
        await downloadZip(ids, '/api/gallery/batch-download', 'fotos-boda.zip');
      } else {
        downloadIndividuals(ids.map((id) => `${API_BASE}/api/gallery/${id}/download`)).catch(() => {});
      }
      setShowDialog(false);
      selection.exit();
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloadBusy(null);
    }
  };

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
      <SelectionToolbar
        selectMode={selection.selectMode}
        count={selection.count}
        busy={selectingAll}
        onSelectAll={handleSelectAll}
        onClear={selection.clear}
        onDownload={() => {
          setDownloadError(null);
          setShowDialog(true);
        }}
      />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {photos.map((photo, idx) => {
          const isSelected = selection.selectMode && selection.selectedIds.has(photo.id);
          return (
            <button
              key={photo.id || idx}
              onClick={() => handlePhotoClick(photo, idx)}
              {...(!selection.selectMode ? lp.handlers(photo.id) : {})}
              onContextMenu={(e) => e.preventDefault()}
              style={{ WebkitTouchCallout: 'none' }}
              className={`relative rounded-xl overflow-hidden shadow-sm bg-white photo-enter cursor-pointer text-left p-0 border-0 select-none ${
                isSelected ? 'ring-2 ring-[var(--color-primary)]' : ''
              }`}
            >
              <img
                src={thumbnailUrl(photo.thumbnail_path)}
                alt={photo.message || 'Foto'}
                className="aspect-square object-cover w-full"
                loading="lazy"
              />
              {selection.selectMode && (
                <span
                  className={`absolute top-2 right-2 w-6 h-6 rounded-full border-2 flex items-center justify-center text-white text-xs ${
                    isSelected
                      ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                      : 'bg-black/30 border-white'
                  }`}
                >
                  {isSelected ? '✓' : ''}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {!selection.selectMode && selectedIdx !== null && (
        <PhotoLightbox
          photos={photos}
          index={selectedIdx}
          onClose={() => setSelectedIdx(null)}
          onNavigate={setSelectedIdx}
        />
      )}

      {showDialog && (
        <DownloadDialog
          count={selection.count}
          busy={downloadBusy}
          error={downloadError}
          onZip={() => handleDownload('zip')}
          onIndividual={() => handleDownload('individual')}
          onClose={() => {
            if (!downloadBusy) setShowDialog(false);
          }}
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
