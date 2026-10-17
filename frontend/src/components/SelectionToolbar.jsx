export default function SelectionToolbar({
  selectMode,
  count,
  busy = false,
  onEnter,
  onExit,
  onSelectAll,
  onClear,
  onDownload,
}) {
  if (!selectMode) {
    return (
      <div className="flex justify-end mb-3">
        <button
          onClick={onEnter}
          className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition cursor-pointer"
        >
          Seleccionar
        </button>
      </div>
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
      <button
        onClick={onExit}
        disabled={busy}
        className="text-sm px-3 py-1.5 rounded-lg text-gray-500 hover:text-gray-700 transition cursor-pointer disabled:opacity-50"
      >
        Cancelar
      </button>
    </div>
  );
}
