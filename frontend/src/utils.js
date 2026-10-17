import { API_BASE } from './api';

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
