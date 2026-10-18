import { Ear, Mic, NotebookPen, Pencil } from "lucide-react";

const COPY = {
  UnclearAudio: { title: "Let’s try that again" },
  NotANote: {
    title: "That didn’t sound like a note",
    hint: "Say what you want to remember, for example “Ravi owes me 500 rupees”.",
  },
};

export default function RejectionNotice({ rejection, onRecordAgain, onEditText, onKeepAnyway, busy }) {
  const { code, message, transcript, attempt } = rejection;
  const fromAudio = attempt.kind === "audio";

  return (
    <div role="alert" className="surface w-full animate-rise p-5 text-left">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-400/10 text-amber-300 ring-1 ring-inset ring-amber-400/20">
          <Ear size={18} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-lg font-semibold text-white">{COPY[code].title}</h2>
          <p className="mt-1 text-sm leading-relaxed text-slate-400">{COPY[code].hint || message}</p>
          {transcript && (
            <p className="mt-3 rounded-lg bg-ink-950/60 px-3 py-2 text-sm text-slate-300 ring-1 ring-white/6">
              <span className="text-xs text-slate-500">Heard </span>
              <span className="italic">“{transcript}”</span>
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {code === "NotANote" && (
          <button type="button" onClick={onKeepAnyway} disabled={busy} className="btn-ghost text-xs">
            <NotebookPen size={15} aria-hidden="true" />
            Save as a note anyway
          </button>
        )}
        {fromAudio ? (
          <button type="button" onClick={onRecordAgain} disabled={busy} className="btn-primary">
            <Mic size={16} aria-hidden="true" />
            Record again
          </button>
        ) : (
          <button type="button" onClick={onEditText} disabled={busy} className="btn-primary">
            <Pencil size={16} aria-hidden="true" />
            Edit text
          </button>
        )}
      </div>
    </div>
  );
}
