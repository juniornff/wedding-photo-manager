import { useState, useEffect, useCallback, useRef } from 'react';
import PhotoGrid from '../components/PhotoGrid';
import PhotoUpload from '../components/PhotoUpload';
import { useSSE } from '../context/useSSE';
import { API_BASE, api } from '../api';

function photoUrl(photo) {
  if (photo.path) return `${API_BASE}/api/uploads/${photo.path}`;
  return '';
}

export default function MainPage() {
  const [info, setInfo] = useState(null);
  const [carousel, setCarousel] = useState([]);
  const [carouselIdx, setCarouselIdx] = useState(0);
  const intervalRef = useRef(null);
  const { lastEvent } = useSSE();

  useEffect(() => {
    api('/api/wedding-info').then((data) => {
      setInfo(data);
      if (data.color_scheme) {
        const colors = data.color_scheme.split(',').map((c) => c.trim());
        if (colors[0]) document.documentElement.style.setProperty('--color-primary', colors[0]);
        if (colors[1]) document.documentElement.style.setProperty('--color-secondary', colors[1]);
        if (colors[2]) document.documentElement.style.setProperty('--color-accent', colors[2]);
        if (colors[3]) document.documentElement.style.setProperty('--color-bg', colors[3]);
        if (colors[4]) document.documentElement.style.setProperty('--color-text', colors[4]);
      }
    }).catch(() => {});
    api('/api/carousel').then(setCarousel).catch(() => {});
  }, []);

  useEffect(() => {
    if (carousel.length === 0) return;
    const interval = (info?.carousel_interval || 5) * 1000;
    const id = setInterval(() => {
      setCarouselIdx((prev) => (prev + 1) % carousel.length);
    }, interval);
    intervalRef.current = id;
    return () => clearInterval(id);
  }, [carousel.length, info?.carousel_interval]);

  useEffect(() => {
    if (!lastEvent) return;
    if (lastEvent.type === 'info_updated' && lastEvent.data) {
      setInfo(lastEvent.data);
    }
    if (lastEvent.type === 'carousel_updated') {
      api('/api/carousel').then(setCarousel).catch(() => {});
    }
    if (lastEvent.type === 'new_photo') {
      window.dispatchEvent(new CustomEvent('refresh-gallery'));
    }
    if (lastEvent.type === 'gallery_photo_deleted') {
      window.dispatchEvent(new CustomEvent('refresh-gallery'));
    }
  }, [lastEvent]);

  const handleNewPhoto = useCallback(() => {
    window.dispatchEvent(new CustomEvent('refresh-gallery'));
  }, []);

  return (
    <div className="min-h-screen">
      {info && (
        <section className="relative overflow-hidden w-full h-[54vh] lg:h-[80vh]">
          {carousel.length > 0 && (
            <div className="absolute inset-0">
              {carousel.map((photo, idx) => (
<div
                    key={photo.id}
                    className="absolute inset-0 transition-opacity duration-1000"
                    style={{ opacity: idx === carouselIdx ? 1 : 0 }}
                  >
                    <img
                      src={photoUrl(photo)}
                      alt=""
                      className="absolute inset-0 w-full h-full object-cover blur-2xl brightness-75 scale-125"
                    />
                    <img
                      src={photoUrl(photo)}
                      alt=""
                      className="relative w-full h-full object-contain"
                    />
                  </div>
              ))}
            </div>
          )}
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center text-center px-4"
            style={{ backgroundColor: carousel.length > 0 ? 'transparent' : 'var(--color-secondary)' }}
          >
            <div className="bg-black/50 rounded-xl p-6 md:p-8 backdrop-blur-sm inline-block">
              <h1 className="text-3xl md:text-5xl font-bold mb-2 text-white">
                {info.novio1_name} & {info.novio2_name}
              </h1>
              <p className="text-lg text-white/90">{info.wedding_date}</p>
            </div>
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
