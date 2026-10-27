import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { startDriveJob } from '../driveJobs';
import DownloadDialog from './DownloadDialog';

vi.mock('../api', () => ({
  api: vi.fn(),
  apiUpload: vi.fn(),
  apiBlob: vi.fn(),
  API_BASE: '',
}));
vi.mock('../driveJobs', () => ({
  startDriveJob: vi.fn(),
  resumeDriveJobs: vi.fn(),
}));
vi.mock('../context/useAuth', () => ({
  useAuth: () => ({ user: { id: 5 } }),
}));

function renderDialog(props = {}) {
  const handlers = {
    onZip: vi.fn(),
    onIndividual: vi.fn(),
    onDriveComplete: vi.fn(),
    onClose: vi.fn(),
  };
  const utils = render(
    <DownloadDialog count={3} {...handlers} {...props} />
  );
  return { ...utils, ...handlers };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.mockResolvedValue({ google_linked: false, drive_ready: false });
});

describe('DownloadDialog', () => {
  it('pluraliza el título según el conteo', () => {
    renderDialog({ count: 1 });
    expect(screen.getByRole('heading', { name: 'Descargar 1 foto' })).toBeInTheDocument();
  });

  it('muestra el error del lote', () => {
    renderDialog({ error: 'Demasiadas fotos' });
    expect(screen.getByText('Demasiadas fotos')).toBeInTheDocument();
  });

  it('el ZIP bloquea con más de 100 fotos y muestra la alternativa', () => {
    const { onZip } = renderDialog({ count: 101 });
    const zip = screen.getByRole('button', { name: 'ZIP único' });
    expect(zip).toBeDisabled();
    expect(screen.getByText(/máximo 100 fotos/)).toBeInTheDocument();

    // individuales sigue disponible
    expect(screen.getByRole('button', { name: 'Archivos individuales' })).toBeEnabled();
    expect(onZip).not.toHaveBeenCalled();
  });

  it('exactamente 100 fotos permite el ZIP', () => {
    renderDialog({ count: 100 });
    expect(screen.getByRole('button', { name: 'ZIP único' })).toBeEnabled();
  });

  it('busy muestra los textos de progreso y bloquea botones', () => {
    renderDialog({ busy: 'zip' });
    expect(screen.getByRole('button', { name: 'Generando ZIP…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Archivos individuales' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
  });

  it('los callbacks de descarga se invocan con clic', async () => {
    const user = userEvent.setup();
    const { onZip, onIndividual } = renderDialog();

    await user.click(screen.getByRole('button', { name: 'ZIP único' }));
    await user.click(screen.getByRole('button', { name: 'Archivos individuales' }));

    expect(onZip).toHaveBeenCalledTimes(1);
    expect(onIndividual).toHaveBeenCalledTimes(1);
  });

  it('clic en el backdrop cierra, pero no con busy', async () => {
    const user = userEvent.setup();
    const { onClose } = renderDialog();
    await user.click(document.querySelector('.fixed.inset-0'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('sin prop drive no hay sección de Google Drive', async () => {
    renderDialog();
    expect(screen.queryByRole('button', { name: /Google Drive/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Google Drive/ })).not.toBeInTheDocument();
    // el status de Drive se precarga siempre al montar (el efecto corre con user.id)
    await waitFor(() => expect(api).toHaveBeenCalledWith('/api/drive/status?user_id=5'));
  });

  it('con drive pero cuenta no vinculada no muestra la opción', async () => {
    renderDialog({ drive: { photoIds: [1], kind: 'gallery' } });
    await waitFor(() => expect(api).toHaveBeenCalledWith('/api/drive/status?user_id=5'));
    expect(screen.queryByRole('button', { name: 'Guardar en Google Drive' })).not.toBeInTheDocument();
  });

  it('cuenta vinculada con Drive listo ofrece guardar', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: true });
    renderDialog({ drive: { photoIds: [1, 2], kind: 'gallery' } });

    expect(await screen.findByRole('button', { name: 'Guardar en Google Drive' })).toBeEnabled();
  });

  it('sin autorizar Drive ofrece el enlace de consentimiento incremental', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: false });
    renderDialog({ drive: { photoIds: [1], kind: 'gallery' } });

    const link = await screen.findByRole('link', { name: 'Autorizar Google Drive' });
    expect(link).toHaveAttribute('href', '/api/google?user_id=5&drive=1');
  });

  it('guardar en Drive cierra el diálogo y avisa al padre', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: true });
    startDriveJob.mockResolvedValue({ job_id: 'j1', total: 2 });
    const user = userEvent.setup();
    const { onDriveComplete, onClose } = renderDialog({
      drive: { photoIds: [1, 2], kind: 'gallery' },
    });

    await user.click(await screen.findByRole('button', { name: 'Guardar en Google Drive' }));

    expect(startDriveJob).toHaveBeenCalledWith({ userId: 5, photoIds: [1, 2], kind: 'gallery' });
    await waitFor(() => expect(onDriveComplete).toHaveBeenCalledTimes(1));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('error drive_reconnect muestra el aviso de caducidad', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: true });
    startDriveJob.mockRejectedValue(new Error('drive_reconnect'));
    const user = userEvent.setup();
    renderDialog({ drive: { photoIds: [1], kind: 'gallery' } });

    await user.click(await screen.findByRole('button', { name: 'Guardar en Google Drive' }));

    expect(
      await screen.findByText(/autorización de Drive caducó/)
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Autorizar Google Drive' })).toBeInTheDocument();
  });

  it('error drive_not_authorized pasa el diálogo a estado de autorización', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: true });
    startDriveJob.mockRejectedValue(new Error('drive_not_authorized'));
    const user = userEvent.setup();
    renderDialog({ drive: { photoIds: [1], kind: 'gallery' } });

    await user.click(await screen.findByRole('button', { name: 'Guardar en Google Drive' }));

    expect(await screen.findByRole('link', { name: 'Autorizar Google Drive' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Guardar en Google Drive' })).not.toBeInTheDocument();
  });

  it('error genérico de Drive se muestra en el diálogo', async () => {
    api.mockResolvedValue({ google_linked: true, drive_ready: true });
    startDriveJob.mockRejectedValue(new Error('drive_error'));
    const user = userEvent.setup();
    renderDialog({ drive: { photoIds: [1], kind: 'gallery' } });

    await user.click(await screen.findByRole('button', { name: 'Guardar en Google Drive' }));
    expect(await screen.findByText('drive_error')).toBeInTheDocument();
  });
});
