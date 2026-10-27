import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import useLongPress from './useLongPress';

const LONG_PRESS_MS = 500;

function pointer(x, y) {
  return { clientX: x, clientY: y };
}

function setup(onLongPress = vi.fn()) {
  const hook = renderHook(() => useLongPress(onLongPress));
  return { onLongPress, ...hook };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useLongPress', () => {
  it('dispara onLongPress con el id tras 500ms', () => {
    const { result, onLongPress } = setup();
    act(() => result.current.handlers(7).onPointerDown(pointer(10, 10)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS));
    expect(onLongPress).toHaveBeenCalledTimes(1);
    expect(onLongPress).toHaveBeenCalledWith(7);
  });

  it('no dispara si el dedo se levanta antes de tiempo', () => {
    const { result, onLongPress } = setup();
    act(() => result.current.handlers(7).onPointerDown(pointer(0, 0)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS - 1));
    act(() => result.current.handlers(7).onPointerUp());
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS + 10));
    expect(onLongPress).not.toHaveBeenCalled();
  });

  it('no dispara si el puntero se mueve más de 10px', () => {
    const { result, onLongPress } = setup();
    act(() => result.current.handlers(7).onPointerDown(pointer(0, 0)));
    act(() => result.current.handlers(7).onPointerMove(pointer(11, 0)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS + 10));
    expect(onLongPress).not.toHaveBeenCalled();
  });

  it('un movimiento exacto de 10px no cancela (umbral estricto)', () => {
    const { result, onLongPress } = setup();
    act(() => result.current.handlers(7).onPointerDown(pointer(0, 0)));
    act(() => result.current.handlers(7).onPointerMove(pointer(10, 10)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS));
    expect(onLongPress).toHaveBeenCalledTimes(1);
  });

  it('consumeClick devuelve true solo después de disparar', () => {
    const { result, onLongPress } = setup();

    // sin disparar → no consume el clic
    expect(result.current.consumeClick()).toBe(false);

    act(() => result.current.handlers(3).onPointerDown(pointer(5, 5)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS));
    expect(onLongPress).toHaveBeenCalledWith(3);

    // el clic posterior al long-press se consume una sola vez
    expect(result.current.consumeClick()).toBe(true);
    expect(result.current.consumeClick()).toBe(false);
  });

  it('cancelar por movimiento no consume el clic (sigue siendo un clic normal)', () => {
    const { result, onLongPress } = setup();
    act(() => result.current.handlers(3).onPointerDown(pointer(0, 0)));
    act(() => result.current.handlers(3).onPointerMove(pointer(50, 0)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS + 10));
    expect(onLongPress).not.toHaveBeenCalled();
    expect(result.current.consumeClick()).toBe(false);
  });

  it('un nuevo press reinicia el estado', () => {
    const { result, onLongPress } = setup();
    // primer press cancelado por movimiento
    act(() => result.current.handlers(1).onPointerDown(pointer(0, 0)));
    act(() => result.current.handlers(1).onPointerMove(pointer(99, 99)));
    // segundo press limpio dispara con el id nuevo
    act(() => result.current.handlers(2).onPointerDown(pointer(0, 0)));
    act(() => vi.advanceTimersByTime(LONG_PRESS_MS));
    expect(onLongPress).toHaveBeenCalledTimes(1);
    expect(onLongPress).toHaveBeenCalledWith(2);
  });
});
