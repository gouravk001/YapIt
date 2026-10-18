import { Check, LoaderCircle, Mic, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { isEmptyValue } from "../lib/format";
import { typeLabel } from "../lib/noteTypes";
import FieldInput from "./FieldInput";
import TypeIcon from "./TypeIcon";
import TypePicker from "./TypePicker";

const COPY = {
  review: { eyebrow: "Review draft", title: "Does this look right?", submit: "Save note", cancel: "Discard" },
  edit: { eyebrow: "Edit note", title: "Make your changes", submit: "Save changes", cancel: "Cancel" },
};

export default function ReviewForm({
  draft,
  types = [],
  onConfirm,
  onDiscard,
  onRetype,
  isRetyping = false,
  isSaving = false,
  mode = "review",
}) {
  const [prevDraft, setPrevDraft] = useState(draft);
  const [fields, setFields] = useState(draft.fields || {});
  const [summary, setSummary] = useState(draft.summary || "");
  const [requestedType, setRequestedType] = useState(draft.type_name);

  if (draft !== prevDraft) {
    setPrevDraft(draft);
    setFields(draft.fields || {});
    setSummary(draft.summary || "");
    setRequestedType(draft.type_name);
  }

  const copy = COPY[mode];
  const typeDef = types.find((t) => t.name === draft.type_name) || { fields: [] };
  const busy = isRetyping || isSaving;
  const shownType = isRetyping ? requestedType : draft.type_name;

  const handleTypeChange = (typeName) => {
    setRequestedType(typeName);
    onRetype(typeName);
  };

  const isMissing = (field) =>
    draft.missing_fields?.includes(field.name) && isEmptyValue(fields[field.name]);

  // A field's warning no longer applies once the user has changed that field.
  const warnings = (draft.warnings || []).filter(
    (w) => !w.field || fields[w.field] === draft.fields?.[w.field],
  );
  const fieldWarning = (field) => warnings.find((w) => w.field === field.name)?.message;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (busy) return;
    onConfirm({
      ...draft,
      summary: summary.trim() || draft.summary,
      fields,
      status: "confirmed",
      missing_fields: [],
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit(e);
  };

  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={handleKeyDown}
      aria-busy={busy}
      className="surface w-full animate-rise text-left"
    >
      <div className="space-y-5 p-5 sm:p-7">
        <header className="flex items-start gap-3.5">
          <TypeIcon typeName={draft.type_name} />
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-accent">{copy.eyebrow}</p>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-white">{copy.title}</h2>
          </div>
        </header>

        {warnings.length > 0 && (
          <div
            role="status"
            className="flex animate-fade-in gap-3 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3.5"
          >
            <TriangleAlert size={18} className="mt-0.5 shrink-0 text-amber-300" aria-hidden="true" />
            <div className="text-sm">
              <p className="font-medium text-amber-100">Double-check this note</p>
              <ul className="mt-1 space-y-0.5 text-amber-200/90">
                {warnings.map((w) => (
                  <li key={`${w.field}-${w.message}`}>{w.message}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        <blockquote className="flex gap-3 rounded-xl bg-ink-950/60 p-3.5 ring-1 ring-white/6">
          <Mic size={16} className="mt-0.5 shrink-0 text-slate-500" aria-label="Transcript" />
          <p className="text-sm italic leading-relaxed text-slate-300">{draft.transcript}</p>
        </blockquote>

        {mode === "review" ? (
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-400">Note type</p>
            <TypePicker types={types} value={shownType} onChange={handleTypeChange} disabled={isRetyping} />
          </div>
        ) : (
          <p className="text-xs text-slate-400">
            Type: <span className="font-medium text-slate-200">{typeLabel(draft.type_name)}</span>
          </p>
        )}

        <div>
          <label htmlFor="note-summary" className="mb-1.5 block text-xs font-medium text-slate-300">
            Summary
          </label>
          <input
            id="note-summary"
            type="text"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            required
            className="field-input text-base font-medium"
          />
        </div>

        <div className="relative">
          {isRetyping && (
            <div className="absolute inset-0 z-10 flex animate-fade-in items-center justify-center gap-2 rounded-xl bg-ink-850/80 text-sm text-slate-300 backdrop-blur-sm">
              <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
              Re-reading as {typeLabel(requestedType)}…
            </div>
          )}
          <fieldset disabled={isRetyping} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <legend className="sr-only">Details</legend>
            {typeDef.fields.map((field) => (
              <FieldInput
                key={`${draft.id}-${field.name}`}
                field={field}
                value={fields[field.name]}
                missing={isMissing(field)}
                warning={fieldWarning(field)}
                onChange={(value) => setFields((prev) => ({ ...prev, [field.name]: value }))}
              />
            ))}
          </fieldset>
        </div>
      </div>

      <footer className="flex flex-col-reverse gap-2 border-t border-white/6 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-7">
        <p className="hidden text-xs text-slate-500 sm:block">
          <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span> to save
        </p>
        <div className="flex flex-col-reverse gap-2 sm:flex-row">
          <button type="button" onClick={onDiscard} disabled={isSaving} className="btn-ghost">
            {copy.cancel}
          </button>
          <button type="submit" disabled={busy} className="btn-primary min-w-32">
            {isSaving ? (
              <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Check size={16} aria-hidden="true" />
            )}
            {warnings.length > 0 ? "Save anyway" : copy.submit}
          </button>
        </div>
      </footer>
    </form>
  );
}
