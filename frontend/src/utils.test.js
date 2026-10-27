import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiBlob } from './api';
import { authorName, downloadIndividuals, downloadZip, photoSrc, photoUrl, thumbnailUrl } from './utils';

vi.mock('./api', () => ({
  API_BASE: '',
  api: vi.fn(),
  apiUpload: vi.fn(),
  apiBlob: vi.fn(),
}));

describe('photoUrl / thumbnailUrl', () => {
  it('prefija las rutas con el endpoint de uploads', () => {
    expect(photoUrl('Galeria/a.jpg')).toBe('/api/uploads/Galeria/a.jpg');
  });

  it('prefija las rutas con el endpoint de miniaturas', () => {
    expect(thumbnailUrl('Galeria/a.jpg')).toBe('/api/thumbnails/Galeria/a.jpg');
  });
});

describe('photoSrc', () => {
  it('devuelve cadena vacía sin foto', () => {
    expect(photoSrc(null)).toBe('');
    expect(photoSrc(undefined)).toBe('');
    expect(photoSrc({})).toBe('');
  });

  it('prefiere la miniatura cuando existe', () => {
    const src = photoSrc({ thumbnail_path: 'Galeria/t.jpg', path: 'Galeria/a.jpg' });
    expect(src).toBe('/api/thumbnails/Galeria/t.jpg');
  });

  it('cae a la foto completa si no hay miniatura', () => {
    expect(photoSrc({ path: 'Galeria/a.jpg' })).toBe('/api/uploads/Galeria/a.jpg');
  });
});

describe('authorName', () => {
  it('prioriza el nombre de Google sobre el alias', () => {
    expect(authorName({ user_google_name: 'Ana', user_alias: 'anita' })).toBe('Ana');
  });

  it('usa el alias si no hay nombre de Google', () => {
    expect(authorName({ user_alias: 'anita' })).toBe('anita');
  });

  it('cae a Anónimo sin autor (fotos de autor borrado)', () => {
    expect(authorName({ user_alias: null })).toBe('Anónimo');
    expect(authorName(null)).toBe('Anónimo');
  });
});

describe('downloadZip', () => {
  let clickSpy;

  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => 'blob:zip');
    URL.revokeObjectURL = vi.fn();
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('descarga el blob devuelto con el nombre indicado', async () => {
    const blob = new Blob(['PK'], { type: 'application/zip' });
    apiBlob.mockResolvedValue(blob);

    await downloadZip([1, 2, 3], '/api/gallery/batch-download', 'fotos.zip');

    expect(apiBlob).toHaveBeenCalledWith('/api/gallery/batch-download', {
      method: 'POST',
      body: JSON.stringify({ photo_ids: [1, 2, 3] }),
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:zip');
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it('propaga el error de la API', async () => {
    apiBlob.mockRejectedValue(new Error('Demasiadas fotos'));
    await expect(downloadZip([1], '/x', 'a.zip')).rejects.toThrow('Demasiadas fotos');
    expect(clickSpy).not.toHaveBeenCalled();
  });
});

describe('downloadIndividuals', () => {
  const clicked = [];

  beforeEach(() => {
    vi.useFakeTimers();
    clicked.length = 0;
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      clicked.push(this.href);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('hace clic en cada url con retardo entre ellas', async () => {
    const urls = ['/api/uploads/a.jpg', '/api/uploads/b.jpg', '/api/uploads/c.jpg'];
    const promise = downloadIndividuals(urls, 400);

    // el primero es inmediato
    await vi.advanceTimersByTimeAsync(0);
    expect(clicked).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(400);
    expect(clicked).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(400);
    expect(clicked).toHaveLength(3);

    await promise;
    expect(clicked[0]).toContain('/api/uploads/a.jpg');
    expect(clicked[2]).toContain('/api/uploads/c.jpg');
  });

  it('con una sola url no espera', async () => {
    await downloadIndividuals(['/api/uploads/only.jpg'], 400);
    expect(clicked).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
  });
});
