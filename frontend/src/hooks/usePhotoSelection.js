import { useCallback, useEffect, useState } from 'react';

export default function usePhotoSelection() {
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(() => new Set());

  useEffect(() => {
    if (selectMode && selectedIds.size === 0) setSelectMode(false);
  }, [selectMode, selectedIds]);

  const enter = useCallback(() => setSelectMode(true), []);

  const exit = useCallback(() => {
    setSelectMode(false);
    setSelectedIds(new Set());
  }, []);

  const toggle = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback((ids) => setSelectedIds(new Set(ids)), []);

  const clear = useCallback(() => setSelectedIds(new Set()), []);

  const remove = useCallback((id) => {
    setSelectedIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const prune = useCallback((ids) => {
    const valid = new Set(ids);
    setSelectedIds((prev) => new Set([...prev].filter((id) => valid.has(id))));
  }, []);

  return {
    selectMode,
    selectedIds,
    count: selectedIds.size,
    enter,
    exit,
    toggle,
    selectAll,
    clear,
    remove,
    prune,
  };
}
