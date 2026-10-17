export default function DownloadDialog({ count, busy, error, onZip, onIndividual, onClose }) {
  const zipBlocked = count > 100;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70] p-4"
      onClick={busy ? undefined : onClose}
    >
      <div
        className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-semibold text-lg mb-1">
          Descargar {count} foto{count === 1 ? '' : 's'}
        </h3>
        <p className="text-sm text-gray-500 mb-4">¿Cómo quieres descargarlas?</p>

        {error && <p className="text-sm text-red-500 mb-3">{error}</p>}

        <div className="space-y-2">
          <button
            onClick={onZip}
            disabled={busy || zipBlocked}
            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer disabled:opacity-50"
          >
            {busy === 'zip' ? 'Generando ZIP…' : 'ZIP único'}
          </button>
          {zipBlocked && (
            <p className="text-xs text-gray-400">
              El ZIP admite máximo 100 fotos; usa archivos individuales o reduce la selección.
            </p>
          )}
          <button
            onClick={onIndividual}
            disabled={busy}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition cursor-pointer disabled:opacity-50"
          >
            {busy === 'individual' ? 'Iniciando descargas…' : 'Archivos individuales'}
          </button>
          <p className="text-xs text-gray-400">
            Tu navegador puede pedir permiso para descargar varios archivos a la vez.
          </p>
        </div>

        <button
          onClick={onClose}
          disabled={busy}
          className="mt-3 w-full text-sm text-gray-500 hover:text-gray-700 cursor-pointer disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
