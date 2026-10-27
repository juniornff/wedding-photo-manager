import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import usePhotoSelection from './usePhotoSelection';

function setup() {
  return renderHook(() => usePhotoSelection());
}

// La UI real entra al modo selección en el mismo batch: enter() + toggle(id)
// (PhotoGrid long-press). Con selección vacía, enter() se auto-apaga.
function enterWith(result, ...ids) {
  act(() => {
    result.current.enter();
    ids.forEach((id) => result.current.toggle(id));
  });
}

describe('usePhotoSelection', () => {
  it('arranca en modo normal sin selección', () => {
    const { result } = setup();
    expect(result.current.selectMode).toBe(false);
    expect(result.current.count).toBe(0);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it('enter con selección vacía no mantiene el modo (auto-protección)', () => {
    const { result } = setup();
    act(() => result.current.enter());
    expect(result.current.selectMode).toBe(false);
  });

  it('enter + foto seleccionada activa el modo', () => {
    const { result } = setup();
    enterWith(result, 1);
    expect(result.current.selectMode).toBe(true);
    expect(result.current.count).toBe(1);
  });

  it('toggle agrega y quita ids', () => {
    const { result } = setup();
    enterWith(result, 1);
    act(() => result.current.toggle(2));
    expect(result.current.count).toBe(2);
    expect(result.current.selectedIds.has(1)).toBe(true);

    act(() => result.current.toggle(1));
    expect(result.current.count).toBe(1);
    expect(result.current.selectedIds.has(1)).toBe(false);
    expect(result.current.selectMode).toBe(true); // aún queda 2 seleccionada
  });

  it('selectAll reemplaza la selección y clear la vacía', () => {
    const { result } = setup();
    enterWith(result, 99);
    act(() => result.current.selectAll([1, 2, 3]));
    expect(result.current.count).toBe(3);
    expect(result.current.selectedIds.has(99)).toBe(false);

    act(() => result.current.clear());
    expect(result.current.count).toBe(0);
  });

  it('exit limpia la selección y desactiva el modo', () => {
    const { result } = setup();
    enterWith(result, 1);
    expect(result.current.selectMode).toBe(true);

    act(() => result.current.exit());
    expect(result.current.selectMode).toBe(false);
    expect(result.current.count).toBe(0);
  });

  it('quedar sin selección desactiva el modo solo (regla de la UI)', () => {
    const { result } = setup();
    enterWith(result, 1);
    expect(result.current.selectMode).toBe(true);

    // deseleccionar la última foto sale del modo selección
    act(() => result.current.remove(1));
    expect(result.current.count).toBe(0);
    expect(result.current.selectMode).toBe(false);
  });

  it('remove de un id no seleccionado no cambia nada', () => {
    const { result } = setup();
    enterWith(result, 1);
    act(() => result.current.remove(404));
    expect(result.current.count).toBe(1);
    expect(result.current.selectMode).toBe(true);
  });

  it('prune descarta ids que ya no existen (fotos borradas)', () => {
    const { result } = setup();
    act(() => {
      result.current.enter();
      result.current.selectAll([1, 2, 3]);
    });
    act(() => result.current.prune([2, 9]));
    expect([...result.current.selectedIds]).toEqual([2]);
    expect(result.current.selectMode).toBe(true); // aún queda una seleccionada
  });

  it('prune con la última foto válida sale del modo', () => {
    const { result } = setup();
    enterWith(result, 1);
    act(() => result.current.prune([]));
    expect(result.current.count).toBe(0);
    expect(result.current.selectMode).toBe(false);
  });
});
