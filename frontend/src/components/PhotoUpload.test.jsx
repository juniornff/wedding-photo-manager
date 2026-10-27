import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiUpload } from '../api';
import PhotoUpload from './PhotoUpload';

vi.mock('../api', () => ({
  api: vi.fn(),
  apiUpload: vi.fn(),
  apiBlob: vi.fn(),
  API_BASE: '',
}));
vi.mock('../context/useAuth', () => ({
  useAuth: () => ({ user: authState.user }),
}));

const authState = vi.hoisted(() => ({ user: { id: 7, alias: 'Fotografa' } }));

function renderUpload(props = {}) {
  const onSuccess = vi.fn();
  const utils = render(<PhotoUpload uploadUrl="/api/gallery/upload" onSuccess={onSuccess} {...props} />);
  return { ...utils, onSuccess };
}

async function openDialog(user) {
  await user.click(screen.getByRole('button', { name: 'Subir foto' }));
  return screen.getByRole('heading', { name: 'Subir foto' });
}

function fileInput() {
  return document.querySelector('input[type="file"]');
}

beforeEach(() => {
  vi.clearAllMocks();
  authState.user = { id: 7, alias: 'Fotografa' };
});

describe('PhotoUpload', () => {
  it('sin sesión no abre el formulario y pide login', async () => {
    authState.user = null;
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
    const user = userEvent.setup();
    renderUpload();

    await user.click(screen.getByRole('button', { name: 'Subir foto' }));

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'show-login' })
    );
    expect(screen.queryByRole('heading', { name: 'Subir foto' })).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it('abre el formulario y acepta archivo + mensaje', async () => {
    const user = userEvent.setup();
    renderUpload();
    await openDialog(user);

    const input = fileInput();
    await user.upload(input, new File(['x'], 'foto.jpg', { type: 'image/jpeg' }));

    const textarea = screen.getByPlaceholderText(/Máx 150 caracteres/i);
    await user.type(textarea, 'qué bonita');
    expect(textarea).toHaveValue('qué bonita');
  });

  it('el mensaje se recorta a 150 caracteres', async () => {
    const user = userEvent.setup();
    renderUpload();
    await openDialog(user);
    await user.upload(fileInput(), new File(['x'], 'a.jpg', { type: 'image/jpeg' }));

    const textarea = screen.getByPlaceholderText(/Máx 150 caracteres/i);
    await user.type(textarea, 'x'.repeat(160));
    expect(textarea).toHaveValue('x'.repeat(150));
  });

  it('sin archivo el botón Subir está deshabilitado', async () => {
    const user = userEvent.setup();
    renderUpload();
    await openDialog(user);
    expect(screen.getByRole('button', { name: 'Subir' })).toBeDisabled();
  });

  it('sube la foto con file, user_id y mensaje recortado', async () => {
    apiUpload.mockResolvedValue({ id: 42 });
    const user = userEvent.setup();
    const { onSuccess } = renderUpload();

    await openDialog(user);
    const file = new File(['x'], 'foto.jpg', { type: 'image/jpeg' });
    await user.upload(fileInput(), file);
    await user.type(screen.getByPlaceholderText(/Máx 150 caracteres/i), '  hola boda  ');
    await user.click(screen.getByRole('button', { name: 'Subir' }));

    await waitFor(() => expect(apiUpload).toHaveBeenCalledTimes(1));
    const [url, fd] = apiUpload.mock.calls[0];
    expect(url).toBe('/api/gallery/upload');
    expect(fd.get('file')).toBeInstanceOf(File);
    expect(fd.get('user_id')).toBe('7');
    expect(fd.get('message')).toBe('hola boda'); // trim

    expect(await screen.findByText('¡Foto subida con éxito!')).toBeInTheDocument();
    expect(onSuccess).toHaveBeenCalledWith({ id: 42 });
    // el modal se cierra
    expect(screen.queryByRole('heading', { name: 'Subir foto' })).not.toBeInTheDocument();
  });

  it('sin mensaje no se envía el campo message', async () => {
    apiUpload.mockResolvedValue({ id: 1 });
    const user = userEvent.setup();
    renderUpload();

    await openDialog(user);
    await user.upload(fileInput(), new File(['x'], 'a.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Subir' }));

    await waitFor(() => expect(apiUpload).toHaveBeenCalledTimes(1));
    expect(apiUpload.mock.calls[0][1].get('message')).toBeNull();
  });

  it('un error de la API se muestra como notificación', async () => {
    apiUpload.mockRejectedValue(new Error('Rate limit de subidas'));
    const user = userEvent.setup();
    renderUpload();

    await openDialog(user);
    await user.upload(fileInput(), new File(['x'], 'a.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Subir' }));

    expect(await screen.findByText('Rate limit de subidas')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Subir foto' })).toBeInTheDocument(); // sigue abierto
  });

  it('sin id de usuario no sube y avisa', async () => {
    authState.user = { alias: 'sin-id' };
    const user = userEvent.setup();
    renderUpload();

    await openDialog(user);
    await user.upload(fileInput(), new File(['x'], 'a.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Subir' }));

    expect(await screen.findByText('Debes iniciar sesión primero')).toBeInTheDocument();
    expect(apiUpload).not.toHaveBeenCalled();
  });

  it('Cancelar cierra y limpia el formulario', async () => {
    const user = userEvent.setup();
    renderUpload();

    await openDialog(user);
    await user.upload(fileInput(), new File(['x'], 'a.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(screen.queryByRole('heading', { name: 'Subir foto' })).not.toBeInTheDocument();
    // reabrir: no arrastra el archivo anterior
    await openDialog(user);
    expect(screen.getByRole('button', { name: 'Subir' })).toBeDisabled();
  });
});
