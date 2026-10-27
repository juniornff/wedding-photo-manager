import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_BASE, api, apiBlob, apiUpload } from './api';

function jsonResponse(data, { ok = true, status = 200, statusText = 'OK' } = {}) {
  return {
    ok,
    status,
    statusText,
    json: async () => data,
    blob: async () => new Blob(['bin']),
  };
}

let fetchMock;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('API_BASE', () => {
  it('es relativa por defecto (sin VITE_API_URL)', () => {
    expect(API_BASE).toBe('');
  });
});

describe('api', () => {
  it('hace GET con credentials include y parsea JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    const data = await api('/api/gallery');

    expect(data).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith('/api/gallery', expect.objectContaining({
      credentials: 'include',
    }));
    const options = fetchMock.mock.calls[0][1];
    expect(options.headers['Content-Type']).toBe('application/json');
  });

  it('permite sobrescribir headers sin perder los base', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    await api('/x', { headers: { Authorization: 'Bearer t' } });
    const options = fetchMock.mock.calls[0][1];
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(options.headers.Authorization).toBe('Bearer t');
  });

  it('lanza el detail del error del servidor', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Rate limit' }, { ok: false, status: 429 }));
    await expect(api('/x')).rejects.toThrow('Rate limit');
  });

  it('cae a statusText si el error no tiene detail parseable', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => { throw new Error('no json'); },
      blob: async () => new Blob(),
    });
    await expect(api('/x')).rejects.toThrow('Internal Server Error');
  });

  it('devuelve null en 204 sin intentar parsear', async () => {
    const body = { json: vi.fn() };
    fetchMock.mockResolvedValue({ ok: true, status: 204, ...body });
    await expect(api('/api/admin/users/1', { method: 'DELETE' })).resolves.toBeNull();
    expect(body.json).not.toHaveBeenCalled();
  });
});

describe('apiUpload', () => {
  it('hace POST con el FormData tal cual (sin forzar Content-Type)', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 1 }));
    const fd = new FormData();

    const data = await apiUpload('/api/gallery/upload', fd);

    expect(data).toEqual({ id: 1 });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/gallery/upload');
    expect(options.method).toBe('POST');
    expect(options.body).toBe(fd);
    expect(options.credentials).toBe('include');
    expect(options.headers).toBeUndefined();
  });

  it('propaga errores igual que api', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Archivo inválido' }, { ok: false, status: 400 }));
    await expect(apiUpload('/x', new FormData())).rejects.toThrow('Archivo inválido');
  });
});

describe('apiBlob', () => {
  it('devuelve el blob de la respuesta', async () => {
    fetchMock.mockResolvedValue(jsonResponse(null));
    const blob = await apiBlob('/api/gallery/batch-download', { method: 'POST' });
    expect(blob).toBeInstanceOf(Blob);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/gallery/batch-download');
    expect(options.method).toBe('POST');
  });

  it('lanza el detail en errores', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'ZIP demasiado grande' }, { ok: false, status: 413 }));
    await expect(apiBlob('/x')).rejects.toThrow('ZIP demasiado grande');
  });
});
