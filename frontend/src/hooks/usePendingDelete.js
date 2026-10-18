import { useCallback, useEffect, useRef, useState } from "react";

// Hides an item straight away but only calls commit(id) after delayMs, so it can be undone.
// A second delete commits the first; leaving the page commits whatever is pending.
export function usePendingDelete(commit, delayMs) {
  const [pendingId, setPendingId] = useState(null);
  const pendingRef = useRef(null);
  const timerRef = useRef(null);
  const commitRef = useRef(commit);

  useEffect(() => {
    commitRef.current = commit;
  });

  const flush = useCallback(() => {
    clearTimeout(timerRef.current);
    const id = pendingRef.current;
    pendingRef.current = null;
    setPendingId(null);
    if (id) commitRef.current(id);
  }, []);

  const remove = (id) => {
    flush();
    pendingRef.current = id;
    setPendingId(id);
    timerRef.current = setTimeout(flush, delayMs);
  };

  const undo = () => {
    clearTimeout(timerRef.current);
    pendingRef.current = null;
    setPendingId(null);
  };

  useEffect(
    () => () => {
      clearTimeout(timerRef.current);
      if (pendingRef.current) commitRef.current(pendingRef.current);
    },
    [],
  );

  return { pendingId, remove, undo };
}
