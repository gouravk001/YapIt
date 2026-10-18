function envNumber(name, fallback) {
  const value = Number(import.meta.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

// Longest single recording; the backend refuses anything much longer.
export const MAX_RECORDING_SECONDS = envNumber("VITE_MAX_RECORDING_SECONDS", 120);

// When the recording timer starts showing the limit.
export const LIMIT_WARNING_SECONDS = 30;

// How long a deleted note can still be restored with Undo.
export const UNDO_SECONDS = 6;
