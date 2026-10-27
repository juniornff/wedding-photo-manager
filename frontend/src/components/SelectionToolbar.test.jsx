import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import SelectionToolbar from './SelectionToolbar';

function renderToolbar(props = {}) {
  const handlers = {
    onSelectAll: vi.fn(),
    onClear: vi.fn(),
    onDownload: vi.fn(),
  };
  const utils = render(<SelectionToolbar selectMode={false} count={0} {...handlers} {...props} />);
  return { ...utils, ...handlers };
}

describe('SelectionToolbar', () => {
  it('sin modo selección muestra la pista de long-press', () => {
    renderToolbar({ selectMode: false });
    expect(
      screen.getByText('Mantén presionada una foto para seleccionar varias')
    ).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('pluraliza el contador de seleccionadas', () => {
    const { rerender } = renderToolbar({ selectMode: true, count: 1 });
    expect(screen.getByText('1 seleccionada')).toBeInTheDocument();

    rerender(<SelectionToolbar selectMode count={3} onSelectAll={vi.fn()} onClear={vi.fn()} onDownload={vi.fn()} />);
    expect(screen.getByText('3 seleccionadas')).toBeInTheDocument();
  });

  it('muestra el total en el botón de descarga', () => {
    renderToolbar({ selectMode: true, count: 7 });
    expect(screen.getByRole('button', { name: 'Descargar (7)' })).toBeInTheDocument();
  });

  it('invoca los callbacks al hacer clic', async () => {
    const user = userEvent.setup();
    const { onSelectAll, onClear, onDownload } = renderToolbar({ selectMode: true, count: 2 });

    await user.click(screen.getByRole('button', { name: 'Todas' }));
    await user.click(screen.getByRole('button', { name: 'Ninguna' }));
    await user.click(screen.getByRole('button', { name: 'Descargar (2)' }));

    expect(onSelectAll).toHaveBeenCalledTimes(1);
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it('deshabilita Ninguna y Descargar sin selección', () => {
    renderToolbar({ selectMode: true, count: 0 });
    expect(screen.getByRole('button', { name: 'Ninguna' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Descargar (0)' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Todas' })).toBeEnabled();
  });

  it('con busy bloquea todo y cambia el texto de Todas', () => {
    renderToolbar({ selectMode: true, count: 3, busy: true });
    expect(screen.getByRole('button', { name: 'Cargando…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ninguna' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Descargar (3)' })).toBeDisabled();
  });
});
