import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';

const SSEContext = createContext(null);

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
      const es = new EventSource('/api/events');
      esRef.current = es;

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setLastEvent({ type: data.type || 'message', data });
        } catch {
          setLastEvent({ type: 'message', data: e.data });
        }
      };

      es.addEventListener('new_photo', (e) => {
        try { setLastEvent({ type: 'new_photo', data: JSON.parse(e.data) }); }
        catch { setLastEvent({ type: 'new_photo', data: e.data }); }
      });

      es.addEventListener('winner_selected', (e) => {
        try { setLastEvent({ type: 'winner_selected', data: JSON.parse(e.data) }); }
        catch { setLastEvent({ type: 'winner_selected', data: e.data }); }
      });

      es.addEventListener('info_updated', (e) => {
        try { setLastEvent({ type: 'info_updated', data: JSON.parse(e.data) }); }
        catch { setLastEvent({ type: 'info_updated', data: e.data }); }
      });

      es.addEventListener('photo_deleted', (e) => {
        try { setLastEvent({ type: 'photo_deleted', data: JSON.parse(e.data) }); }
        catch { setLastEvent({ type: 'photo_deleted', data: e.data }); }
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

export function useSSE() {
  const ctx = useContext(SSEContext);
  if (!ctx) throw new Error('useSSE must be used within SSEProvider');
  return ctx;
}
