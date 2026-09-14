import { useState, useEffect, useRef } from 'react';
import { SSEContext } from './SSEContext';
import { useAuth } from './useAuth';
import { API_BASE } from '../api';

export function SSEProvider({ children }) {
  const { user } = useAuth();
  const [lastEvent, setLastEvent] = useState(null);
  const esRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    if (!user) {
      if (esRef.current) esRef.current.close();
      return;
    }

    function connect() {
      if (esRef.current) esRef.current.close();
      const es = new EventSource(`${API_BASE}/api/events`);
      esRef.current = es;

      const events = [
        'new_photo',
        'gallery_photo_deleted',
        'carousel_updated',
        'info_updated',
        'new_challenge_photo',
        'challenge_photo_deleted',
        'winner_selected',
      ];

      events.forEach((name) => {
        es.addEventListener(name, (e) => {
          try { setLastEvent({ type: name, data: JSON.parse(e.data) }); }
          catch { setLastEvent({ type: name, data: e.data }); }
        });
      });

      es.onerror = () => {
        es.close();
        retryRef.current = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      if (esRef.current) esRef.current.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [user]);

  return (
    <SSEContext.Provider value={{ lastEvent }}>
      {children}
    </SSEContext.Provider>
  );
}