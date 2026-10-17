export default function SelectionToolbar({ selectMode, count, busy = false, onSelectAll, onClear, onDownload }) {
  if (!selectMode) {
    return (
      <p className="text-xs text-gray-400 text-right mb-3">
        Mantén presionada una foto para seleccionar varias
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mb-3">
      <span className="text-sm font-medium mr-1">
        {count} seleccionada{count === 1 ? '' : 's'}
      </span>
      <button
        onClick={onSelectAll}
        disabled={busy}
        className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition cursor-pointer disabled:opacity-50"
      >
        {busy ? 'Cargando…' : 'Todas'}
      </button>
      <button
        onClick={onClear}
        disabled={count === 0 || busy}
        className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition cursor-pointer disabled:opacity-50"
      >
        Ninguna
      </button>
      <button
        onClick={onDownload}
        disabled={count === 0 || busy}
        className="text-sm px-4 py-1.5 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition cursor-pointer disabled:opacity-50"
      >
        Descargar ({count})
      </button>
    </div>
  );
}
