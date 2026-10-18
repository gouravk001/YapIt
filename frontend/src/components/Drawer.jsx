import { useEffect, useRef } from "react";

export default function Drawer({ label, onClose, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-label={label}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => e.target === ref.current && onClose()}
      className="m-0 h-dvh max-h-dvh w-[min(22rem,88vw)] animate-slide-in border-r border-white/8 bg-ink-900 p-0 text-slate-200 backdrop:bg-ink-950/70 backdrop:backdrop-blur-sm"
    >
      {children}
    </dialog>
  );
}
