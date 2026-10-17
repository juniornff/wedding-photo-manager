import { useEffect, useState } from 'react';
import { resumeDriveJobs } from '../driveJobs';

const DEFAULT_DURATION = { success: 6000, info: 6000, error: 10000 };

const BORDER = {
  success: 'border-l-green-500',
  error: 'border-l-red-500',
  info: 'border-l-[var(--color-primary)]',
};

export default function Toaster() {
  const [toasts, setToasts] = useState([]);

  const dismiss = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  useEffect(() => {
    resumeDriveJobs();
    const onToast = (event) => {
      const toast = event.detail;
      setToasts((prev) => [...prev, toast]);
      setTimeout(
        () => dismiss(toast.id),
        toast.duration ?? DEFAULT_DURATION[toast.type] ?? 6000
      );
    };
    window.addEventListener('app-toast', onToast);
    return () => window.removeEventListener('app-toast', onToast);
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="fixed top-4 right-4 z-[90] flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`bg-white rounded-xl shadow-lg border border-gray-100 border-l-4 ${
            BORDER[toast.type] ?? BORDER.info
          } p-4`}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold text-sm text-gray-800">{toast.title}</p>
            <button
              onClick={() => dismiss(toast.id)}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none cursor-pointer"
              aria-label="Cerrar"
            >
              &times;
            </button>
          </div>
          {toast.message && <p className="text-sm text-gray-600 mt-1">{toast.message}</p>}
          {toast.link && (
            <a
              href={toast.link.href}
              target={toast.link.href.startsWith('/') ? undefined : '_blank'}
              rel="noreferrer"
              className="inline-block mt-2 text-xs text-[var(--color-accent)] hover:underline"
            >
              {toast.link.label}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
