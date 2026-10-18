import { useEffect, useRef } from "react";

export default function Dialog({ label, onClose, children }) {
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
      className="m-auto w-full max-w-2xl bg-transparent p-4 backdrop:bg-ink-950/80 backdrop:backdrop-blur-sm"
    >
      {children}
    </dialog>
  );
}
