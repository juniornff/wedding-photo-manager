import { useCallback, useRef } from 'react';

const LONG_PRESS_MS = 500;
const MOVE_THRESHOLD = 10;

export default function useLongPress(onLongPress) {
  const timerRef = useRef(null);
  const posRef = useRef({ x: 0, y: 0 });
  const idRef = useRef(null);
  const firedRef = useRef(false);

  const cancel = useCallback(() => {
    clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const start = useCallback(
    (id, e) => {
      posRef.current = { x: e.clientX, y: e.clientY };
      idRef.current = id;
      firedRef.current = false;
      cancel();
      timerRef.current = setTimeout(() => {
        firedRef.current = true;
        onLongPress(idRef.current);
      }, LONG_PRESS_MS);
    },
    [cancel, onLongPress]
  );

  const move = useCallback(
    (e) => {
      if (
        Math.abs(e.clientX - posRef.current.x) > MOVE_THRESHOLD ||
        Math.abs(e.clientY - posRef.current.y) > MOVE_THRESHOLD
      ) {
        cancel();
      }
    },
    [cancel]
  );

  const consumeClick = useCallback(() => {
    if (!firedRef.current) return false;
    firedRef.current = false;
    return true;
  }, []);

  const handlers = (id) => ({
    onPointerDown: (e) => start(id, e),
    onPointerMove: move,
    onPointerUp: cancel,
    onPointerCancel: cancel,
    onPointerLeave: cancel,
  });

  return { handlers, consumeClick };
}
