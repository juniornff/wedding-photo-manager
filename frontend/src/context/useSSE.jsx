import { useContext } from 'react';
import { SSEContext } from './SSEContext';

export function useSSE() {
  const ctx = useContext(SSEContext);
  if (!ctx) throw new Error('useSSE must be used within SSEProvider');
  return ctx;
}