import { ChevronDown, Pencil, Trash2, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { formatCapturedDateTime, formatCapturedTime, humanize, isEmptyValue } from "../lib/format";
import { typeLabel } from "../lib/noteTypes";
import FieldValue from "./FieldValue";
import TypeIcon from "./TypeIcon";

function fieldEntries(note, typeDef) {
  const definitions = typeDef?.fields || [];
  const known = definitions
    .filter((f) => !isEmptyValue(note.fields?.[f.name]))
    .map((f) => ({ name: f.name, fieldType: f.field_type, value: note.fields[f.name] }));
  const knownNames = new Set(definitions.map((f) => f.name));
  const extra = Object.entries(note.fields || {})
    .filter(([name, value]) => !knownNames.has(name) && !isEmptyValue(value))
    .map(([name, value]) => ({ name, fieldType: null, value }));
  return [...known, ...extra];
}

function DeleteButton({ onDelete }) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="btn-ghost px-2.5 py-1.5 text-xs hover:text-red-300"
      >
        <Trash2 size={14} aria-hidden="true" />
        Delete
      </button>
    );
  }
  return (
    <span className="flex animate-fade-in items-center gap-1" role="group" aria-label="Confirm delete">
      <span className="px-1 text-xs text-slate-400">Delete this note?</span>
      <button
        type="button"
        onClick={onDelete}
        autoFocus
        className="btn px-2.5 py-1.5 text-xs bg-red-500/90 text-white hover:bg-red-500"
      >
        Delete
      </button>
      <button type="button" onClick={() => setConfirming(false)} className="btn-ghost px-2.5 py-1.5 text-xs">
        Keep
      </button>
    </span>
  );
}

export default function NoteCard({ note, typeDef, onDelete, onEdit }) {
  const [expanded, setExpanded] = useState(false);
  const entries = fieldEntries(note, typeDef);
  const needsAttention = note.missing_fields?.length > 0;
  const transcriptId = `transcript-${note.id}`;

  return (
    <article className="group surface animate-rise p-4 transition hover:border-white/15 sm:p-5">
      <div className="flex items-start gap-3.5">
        <TypeIcon typeName={note.type_name} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
            <span className="font-medium text-slate-300">{typeLabel(note.type_name)}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={note.created_at} title={formatCapturedDateTime(note.created_at, note.timezone)}>
              {formatCapturedTime(note.created_at, note.timezone)}
            </time>
            {needsAttention && (
              <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-amber-400/10 px-2 py-0.5 font-medium text-amber-300">
                <TriangleAlert size={12} aria-hidden="true" />
                Needs attention
              </span>
            )}
          </div>

          <h3 className="mt-1 text-[15px] font-semibold leading-snug text-white sm:text-base">
            {note.summary || "Untitled note"}
          </h3>

          {entries.length > 0 && (
            <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              {entries.map(({ name, fieldType, value }) => (
                <div key={name} className="flex min-w-0 items-baseline gap-2">
                  <dt className="shrink-0 text-xs text-slate-500">{humanize(name)}</dt>
                  <dd className="min-w-0 truncate font-medium text-slate-200">
                    <FieldValue fieldType={fieldType} value={value} />
                  </dd>
                </div>
              ))}
            </dl>
          )}

          {expanded && (
            <div id={transcriptId} className="mt-4 animate-fade-in space-y-2 border-t border-white/6 pt-3">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Transcript</p>
              <blockquote className="border-l-2 border-accent/40 pl-3 text-sm italic leading-relaxed text-slate-300">
                {note.transcript}
              </blockquote>
              {needsAttention && (
                <p className="text-xs text-amber-300/90">
                  Missing or invalid: {note.missing_fields.map(humanize).join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-white/6 pt-2.5">
        <button
          type="button"
          onClick={() => setExpanded((open) => !open)}
          aria-expanded={expanded}
          aria-controls={transcriptId}
          className="btn-ghost -ml-2 px-2 py-1.5 text-xs text-slate-400"
        >
          <ChevronDown
            size={14}
            className={`transition-transform ${expanded ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
          {expanded ? "Hide transcript" : "Show transcript"}
        </button>

        <div className="flex items-center gap-1 transition md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100">
          <button type="button" onClick={() => onEdit(note)} className="btn-ghost px-2.5 py-1.5 text-xs">
            <Pencil size={14} aria-hidden="true" />
            Edit
          </button>
          <DeleteButton onDelete={() => onDelete(note.id)} />
        </div>
      </div>
    </article>
  );
}
