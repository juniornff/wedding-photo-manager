import { useState, useEffect, useCallback } from 'react';
import PhotoGrid from '../components/PhotoGrid';
import PhotoUpload from '../components/PhotoUpload';
import { useSSE } from '../context/SSEContext';

function carouselThumbUrl(photo) {
  if (photo.thumbnail_path) return `/api/thumbnails/${photo.thumbnail_path}`;
  if (photo.path) return `/api/uploads/${photo.path}`;
  return '';
}

export default function MainPage() {
  const [info, setInfo] = useState(null);
  const [carousel, setCarousel] = useState([]);
  const { lastEvent } = useSSE();

  useEffect(() => {
    fetch('/api/wedding-info')
      .then((r) => r.json())
      .then(setInfo)
      .catch(() => {});
    fetch('/api/carousel')
      .then((r) => r.json())
      .then(setCarousel)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (lastEvent?.type === 'info_updated' && lastEvent.data) {
      setInfo(lastEvent.data);
    }
  }, [lastEvent]);

  const handleNewPhoto = useCallback(() => {
    window.dispatchEvent(new CustomEvent('refresh-gallery'));
  }, []);

  return (
    <div className="min-h-screen">
      {info && (
        <section
          className="text-center py-10 px-4"
          style={{ backgroundColor: 'var(--color-secondary)' }}
        >
          <h1 className="text-3xl md:text-5xl font-bold mb-2">
            {info.novio1_name} & {info.novio2_name}
          </h1>
          <p className="text-lg opacity-80">{info.wedding_date}</p>
        </section>
      )}

      {carousel.length > 0 && (
        <section className="py-6 px-4">
          <h2 className="text-lg font-semibold mb-3 px-1">Galería de momentos</h2>
          <div className="flex gap-3 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-none">
            {carousel.map((photo, idx) => (
              <div key={photo.id || idx} className="snap-start shrink-0">
                <img
                  src={carouselThumbUrl(photo)}
                  alt=""
                  className="h-48 md:h-64 rounded-xl object-cover shadow-sm"
                />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="max-w-6xl mx-auto px-4 py-6">
        <h2 className="text-lg font-semibold mb-4">Galería de invitados</h2>
        <PhotoGrid fetchUrl="/api/gallery" emptyMessage="Sé el primero en subir una foto" />
      </section>

      <PhotoUpload uploadUrl="/api/gallery/upload" onSuccess={handleNewPhoto} />
    </div>
  );
}
