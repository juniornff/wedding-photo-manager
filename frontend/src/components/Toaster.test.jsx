import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resumeDriveJobs } from '../driveJobs';
import Toaster from './Toaster';

vi.mock('../driveJobs', () => ({
  resumeDriveJobs: vi.fn(),
  startDriveJob: vi.fn(),
}));

function fireToast(detail) {
  act(() => {
    window.dispatchEvent(new CustomEvent('app-toast', { detail }));
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('Toaster', () => {
  it('no renderiza nada sin toasts', () => {
    const { container } = render(<Toaster />);
    expect(container.firstChild).toBeNull();
    // al montar reanuda los jobs de Drive pendientes
    expect(resumeDriveJobs).toHaveBeenCalledTimes(1);
  });

  it('muestra el toast disparado por evento app-toast', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Guardado en Drive', message: '3 fotos', type: 'success' });

    expect(screen.getByText('Guardado en Drive')).toBeInTheDocument();
    expect(screen.getByText('3 fotos')).toBeInTheDocument();
  });

  it('apila varios toasts', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Uno', type: 'info' });
    fireToast({ id: 2, title: 'Dos', type: 'error' });

    expect(screen.getByText('Uno')).toBeInTheDocument();
    expect(screen.getByText('Dos')).toBeInTheDocument();
  });

  it('auto-oculta según la duración del tipo (success 6s, error 10s)', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Éxito', type: 'success' });
    fireToast({ id: 2, title: 'Fallo', type: 'error' });

    act(() => vi.advanceTimersByTime(6000));
    expect(screen.queryByText('Éxito')).not.toBeInTheDocument();
    expect(screen.getByText('Fallo')).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(4000));
    expect(screen.queryByText('Fallo')).not.toBeInTheDocument();
  });

  it('respeta duration explícita del toast', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Rápido', type: 'success', duration: 500 });

    act(() => vi.advanceTimersByTime(500));
    expect(screen.queryByText('Rápido')).not.toBeInTheDocument();
  });

  it('el botón Cerrar elimina el toast al instante', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Cierre manual', type: 'info' });

    act(() => {
      screen.getByRole('button', { name: 'Cerrar' }).click();
    });
    expect(screen.queryByText('Cierre manual')).not.toBeInTheDocument();
  });

  it('renderiza el enlace del toast (interno sin target, externo en nueva pestaña)', () => {
    render(<Toaster />);
    fireToast({
      id: 1,
      title: 'Necesitas autorizar',
      type: 'error',
      link: { href: '/api/google?user_id=3&drive=1', label: 'Autorizar Google Drive' },
    });

    const link = screen.getByRole('link', { name: 'Autorizar Google Drive' });
    expect(link).toHaveAttribute('href', '/api/google?user_id=3&drive=1');
    expect(link).not.toHaveAttribute('target');

    fireToast({
      id: 2,
      title: 'Ver en Drive',
      type: 'success',
      link: { href: 'https://drive.google.com/x', label: 'Abrir carpeta' },
    });
    expect(screen.getByRole('link', { name: 'Abrir carpeta' })).toHaveAttribute('target', '_blank');
  });

  it('un type desconocido usa el borde por defecto (info)', () => {
    render(<Toaster />);
    fireToast({ id: 1, title: 'Raro', type: 'desconocido' });
    const el = screen.getByText('Raro').closest('div').parentElement;
    expect(el.className).toContain('border-l-[var(--color-primary)]');
  });
});
