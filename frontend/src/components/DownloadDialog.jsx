import { useEffect, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../context/useAuth';

const DRIVE_FOLDER_URL = 'https://drive.google.com/drive/folders';

export default function DownloadDialog({
  count,
  busy,
  error,
  drive = null,
  onZip,
  onIndividual,
  onDriveComplete,
  onClose,
}) {
  const zipBlocked = count > 100;
  const { user } = useAuth();
  const [driveStatus, setDriveStatus] = useState(null);
  const [driveProgress, setDriveProgress] = useState(null);
  const [driveResult, setDriveResult] = useState(null);
  const [driveReconnect, setDriveReconnect] = useState(false);

  useEffect(() => {
    if (!user?.id) return;
    let cancelled = false;
    api(`/api/drive/status?user_id=${user.id}`)
      .then((status) => {
        if (!cancelled) setDriveStatus(status);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  const anyBusy = Boolean(busy || driveProgress);

  const handleDrive = async () => {
    const ids = drive?.photoIds ?? [];
    if (!ids.length || !user?.id) return;
    setDriveResult(null);
    setDriveReconnect(false);

    let uploaded = 0;
    let skipped = 0;
    let failed = 0;
    let folderId = null;
    setDriveProgress({ done: 0, total: ids.length });

    for (let i = 0; i < ids.length; i++) {
      try {
        const res = await api('/api/drive/save', {
          method: 'POST',
          body: JSON.stringify({ user_id: user.id, photo_id: ids[i], kind: drive.kind }),
        });
        if (res.status === 'skipped') skipped += 1;
        else uploaded += 1;
        folderId = res.folder_id || folderId;
      } catch (err) {
        if (err.message === 'drive_reconnect') {
          setDriveReconnect(true);
          failed += ids.length - i;
          break;
        }
        if (err.message === 'drive_not_authorized') {
          setDriveStatus((prev) => ({ ...(prev ?? {}), google_linked: true, drive_ready: false }));
          failed += ids.length - i;
          break;
        }
        failed += 1;
      }
      setDriveProgress({ done: i + 1, total: ids.length });
    }

    setDriveProgress(null);
    setDriveResult({ uploaded, skipped, failed, folderId });
    if (failed === 0 && onDriveComplete) onDriveComplete();
  };

  const showDrive = Boolean(drive && driveStatus?.google_linked);
  const driveNeedsAuth = Boolean(driveReconnect || (driveStatus && !driveStatus.drive_ready));
  const driveCompleted = Boolean(driveResult && driveResult.failed === 0);
  const driveSummary = driveResult
    ? [
        driveResult.uploaded > 0 &&
          `${driveResult.uploaded} guardada${driveResult.uploaded === 1 ? '' : 's'}`,
        driveResult.skipped > 0 &&
          `${driveResult.skipped} ya estaba${driveResult.skipped === 1 ? '' : 'n'}`,
        driveResult.failed > 0 && `${driveResult.failed} con error`,
      ]
        .filter(Boolean)
        .join(' · ')
    : '';

  const driveFolderLink = driveResult?.folderId && (
    <a
      href={`${DRIVE_FOLDER_URL}/${driveResult.folderId}`}
      target="_blank"
      rel="noreferrer"
      className="block text-xs text-[var(--color-accent)] hover:underline"
    >
      Abrir carpeta en Google Drive
    </a>
  );

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70] p-4"
      onClick={anyBusy ? undefined : onClose}
    >
      <div
        className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-semibold text-lg mb-1">
          {driveCompleted ? 'Guardado en Google Drive' : `Descargar ${count} foto${count === 1 ? '' : 's'}`}
        </h3>
        {!driveCompleted && <p className="text-sm text-gray-500 mb-4">¿Cómo quieres descargarlas?</p>}

        {error && <p className="text-sm text-red-500 mb-3">{error}</p>}

        {driveCompleted ? (
          <div className="space-y-2">
            <p className="text-sm text-gray-600">Drive: {driveSummary}</p>
            {driveFolderLink}
          </div>
        ) : (
          <div className="space-y-2">
            <button
              onClick={onZip}
              disabled={anyBusy || zipBlocked}
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
              disabled={anyBusy}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition cursor-pointer disabled:opacity-50"
            >
              {busy === 'individual' ? 'Iniciando descargas…' : 'Archivos individuales'}
            </button>
            <p className="text-xs text-gray-400">
              Tu navegador puede pedir permiso para descargar varios archivos a la vez.
            </p>

            {showDrive && (
              <div className="border-t border-gray-100 pt-3 space-y-2">
                {driveNeedsAuth ? (
                  <>
                    {driveReconnect && (
                      <p className="text-sm text-red-500">
                        Tu autorización de Drive caducó o fue revocada. Vuelve a autorizarla para
                        continuar.
                      </p>
                    )}
                    <a
                      href={`/api/google?user_id=${user.id}&drive=1`}
                      className="block w-full text-center px-4 py-2.5 rounded-lg border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-secondary)]/20 transition cursor-pointer"
                    >
                      Autorizar Google Drive
                    </a>
                    <p className="text-xs text-gray-400">
                      Necesario una sola vez: permites crear una carpeta «Fotos Boda» en tu Drive.
                    </p>
                  </>
                ) : (
                  <>
                    <button
                      onClick={handleDrive}
                      disabled={anyBusy}
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-secondary)]/20 transition cursor-pointer disabled:opacity-50"
                    >
                      {driveProgress
                        ? `Guardando ${driveProgress.done}/${driveProgress.total} en Drive…`
                        : 'Guardar en Google Drive'}
                    </button>
                    {driveSummary && <p className="text-sm text-gray-600">Drive: {driveSummary}</p>}
                    {driveFolderLink}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        <button
          onClick={onClose}
          disabled={anyBusy}
          className="mt-3 w-full text-sm text-gray-500 hover:text-gray-700 cursor-pointer disabled:opacity-50"
        >
          {driveResult ? 'Cerrar' : 'Cancelar'}
        </button>
      </div>
    </div>
  );
}
