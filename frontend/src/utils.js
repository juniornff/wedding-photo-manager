import { API_BASE, apiBlob } from './api';

export function photoUrl(path) {
  return `${API_BASE}/api/uploads/${path}`;
}

export function thumbnailUrl(path) {
  return `${API_BASE}/api/thumbnails/${path}`;
}

export function photoSrc(photo) {
  if (!photo) return '';
  if (photo.thumbnail_path) return thumbnailUrl(photo.thumbnail_path);
  if (photo.path) return photoUrl(photo.path);
  return '';
}

export function authorName(photo) {
  return photo?.user_google_name || photo?.user_alias || 'Anónimo';
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function downloadZip(photoIds, endpoint, filename) {
  const blob = await apiBlob(endpoint, {
    method: 'POST',
    body: JSON.stringify({ photo_ids: photoIds }),
  });
  saveBlob(blob, filename);
}

export async function downloadIndividuals(urls, delayMs = 400) {
  for (let i = 0; i < urls.length; i++) {
    const a = document.createElement('a');
    a.href = urls[i];
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
    if (i < urls.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
}
