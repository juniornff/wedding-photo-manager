import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';

export default function PhotoUpload({ uploadUrl, onSuccess }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState(null);
  const fileRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  const showNotification = (msg, type = 'success') => {
    setNotification({ msg, type });
    timerRef.current = setTimeout(() => setNotification(null), 3000);
  };

  const handleUpload = async () => {
    if (!file || !user) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (message.trim()) fd.append('message', message.trim());
      const res = await fetch(uploadUrl, { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Error al subir');
      }
      const data = await res.json();
      showNotification('¡Foto subida con éxito!');
      setOpen(false);
      setFile(null);
      setMessage('');
      if (onSuccess) onSuccess(data);
    } catch (err) {
      showNotification(err.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-[var(--color-primary)] text-white shadow-lg flex items-center justify-center text-3xl hover:scale-110 transition-transform z-40 cursor-pointer"
        aria-label="Subir foto"
      >
        +
      </button>

      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg toast-enter ${
            notification.type === 'error' ? 'bg-red-500 text-white' : 'bg-green-600 text-white'
          }`}
        >
          {notification.msg}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setOpen(false)}>
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-4">Subir foto</h2>

            <input
              type="file"
              accept="image/*"
              ref={fileRef}
              onChange={(e) => setFile(e.target.files[0])}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-[var(--color-secondary)] file:text-[var(--color-text)] hover:file:bg-[var(--color-primary)] hover:file:text-white cursor-pointer"
            />

            {file && (
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value.slice(0, 150))}
                placeholder="Mensaje opcional (máx 150 caracteres)"
                className="mt-4 w-full border rounded-lg p-2 text-sm resize-none h-20"
              />
            )}

            <div className="flex gap-3 mt-4 justify-end">
              <button
                onClick={() => setOpen(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-100 cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm disabled:opacity-50 hover:brightness-110 transition flex items-center gap-2 cursor-pointer"
              >
                {uploading && <span className="spinner" />}
                {uploading ? 'Subiendo...' : 'Subir'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
