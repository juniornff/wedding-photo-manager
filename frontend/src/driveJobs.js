import { api } from './api';
import { showToast } from './toast';

const STORAGE_KEY = 'wedding_drive_jobs';
const POLL_MS = 1500;
const MAX_POLL_FAILURES = 5;
const DRIVE_FOLDER_URL = 'https://drive.google.com/drive/folders';

const active = new Map();

function loadJobs() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveJobs(jobs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch {
    // localStorage no disponible: el sondeo en memoria sigue funcionando
  }
}

function removeJob(jobId) {
  saveJobs(loadJobs().filter((job) => job.jobId !== jobId));
}

function stopPolling(jobId) {
  const interval = active.get(jobId);
  if (interval) {
    clearInterval(interval);
    active.delete(jobId);
  }
}

function finishJob(job, state) {
  stopPolling(job.jobId);
  removeJob(job.jobId);

  const parts = [];
  if (state.uploaded > 0) parts.push(`${state.uploaded} guardada${state.uploaded === 1 ? '' : 's'}`);
  if (state.skipped > 0) parts.push(`${state.skipped} ya estaba${state.skipped === 1 ? '' : 'n'}`);
  if (state.failed > 0) parts.push(`${state.failed} con error`);
  const message = parts.join(' · ');
  const folderLink = state.folder_id
    ? { href: `${DRIVE_FOLDER_URL}/${state.folder_id}`, label: 'Abrir carpeta en Drive' }
    : null;

  if (state.needs_auth) {
    showToast({
      type: 'error',
      title: 'Autoriza Google Drive',
      message:
        'La autorización de Drive caducó o fue revocada. Vuelve a autorizarla y repite la selección.',
      link: { href: `/api/google?user_id=${job.userId}&drive=1`, label: 'Autorizar Google Drive' },
      duration: 12000,
    });
    return;
  }

  if (state.failed > 0) {
    showToast({
      type: 'error',
      title: 'Guardado en Drive con errores',
      message: `${message}. Puedes intentarlo de nuevo.`,
      link: folderLink,
      duration: 12000,
    });
    return;
  }

  showToast({
    type: 'success',
    title: 'Fotos guardadas en Google Drive',
    message,
    link: folderLink,
  });
}

function pollJob(job) {
  if (active.has(job.jobId)) return;
  let failures = 0;
  const interval = setInterval(async () => {
    try {
      const state = await api(`/api/drive/job/${job.jobId}?user_id=${job.userId}`);
      failures = 0;
      if (state.status === 'done') finishJob(job, state);
    } catch {
      failures += 1;
      if (failures >= MAX_POLL_FAILURES) {
        stopPolling(job.jobId);
        removeJob(job.jobId);
        showToast({
          type: 'error',
          title: 'Guardado en Google Drive',
          message: 'No se pudo consultar el estado del guardado. Comprueba tu Drive más tarde.',
        });
      }
    }
  }, POLL_MS);
  active.set(job.jobId, interval);
}

export async function startDriveJob({ userId, photoIds, kind }) {
  const res = await api('/api/drive/save-batch', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, photo_ids: photoIds, kind }),
  });
  const job = { jobId: res.job_id, userId, total: res.total, kind };
  saveJobs([...loadJobs(), job]);
  pollJob(job);
  return job;
}

export function resumeDriveJobs() {
  loadJobs().forEach(pollJob);
}
