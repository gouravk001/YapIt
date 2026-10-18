import { ArrowRight } from "lucide-react";
import { useState } from "react";

export default function TextNoteForm({ initialText = "", onSubmit, onCancel, disabled }) {
  const [text, setText] = useState(initialText);

  const submit = (e) => {
    e.preventDefault();
    if (text.trim()) onSubmit(text.trim());
  };

  return (
    <form onSubmit={submit} className="surface w-full animate-rise p-3 text-left">
      <label htmlFor="typed-note" className="sr-only">
        Type a note
      </label>
      <textarea
        id="typed-note"
        rows={3}
        autoFocus
        placeholder="Ravi owes me 500 rupees, he'll pay next Friday…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(e);
          if (e.key === "Escape") onCancel();
        }}
        className="w-full resize-none bg-transparent px-2 py-1.5 text-sm text-white placeholder:text-slate-500 outline-none"
      />
      <div className="flex items-center justify-between gap-2 border-t border-white/6 pt-2.5">
        <p className="hidden pl-2 text-xs text-slate-500 sm:block">
          <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span>
        </p>
        <div className="ml-auto flex gap-1">
          <button type="button" onClick={onCancel} className="btn-ghost px-3 py-1.5 text-xs">
            Cancel
          </button>
          <button type="submit" disabled={disabled || !text.trim()} className="btn-primary px-3.5 py-1.5 text-xs">
            Process
            <ArrowRight size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
    </form>
  );
}
