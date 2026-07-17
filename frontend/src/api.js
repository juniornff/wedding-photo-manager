export const API_BASE = import.meta.env.VITE_API_URL || '';
const API = API_BASE;

export async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error del servidor');
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function apiUpload(path, formData, options = {}) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error del servidor');
  }
  if (res.status === 204) return null;
  return res.json();
}
