import { RotateCcw } from "lucide-react";
import { useEffect } from "react";

export default function UndoToast({ message, durationMs, onUndo }) {
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key.toLowerCase() === "z" && (e.ctrlKey || e.metaKey) && !e.target.closest("input, textarea")) {
        e.preventDefault();
        onUndo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onUndo]);

  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-6 z-50 mx-auto w-[min(24rem,calc(100vw-2rem))] animate-rise overflow-hidden rounded-xl border border-white/10 bg-ink-800 shadow-2xl shadow-black/50"
    >
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <span className="text-sm text-slate-200">{message}</span>
        <button type="button" onClick={onUndo} className="btn-subtle px-3 py-1.5 text-xs">
          <RotateCcw size={14} aria-hidden="true" />
          Undo
        </button>
      </div>
      <div
        aria-hidden="true"
        className="h-0.5 origin-left animate-shrink bg-accent/70"
        style={{ animationDuration: `${durationMs}ms` }}
      />
    </div>
  );
}
