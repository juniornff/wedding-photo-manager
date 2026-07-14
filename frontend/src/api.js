const API = import.meta.env.VITE_API_URL || '';

export async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error del servidor');
  }
  return res.json();
}

export async function apiUpload(path, formData, options = {}) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    body: formData,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error del servidor');
  }
  return res.json();
}
