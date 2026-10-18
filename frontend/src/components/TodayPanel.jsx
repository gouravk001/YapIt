import { ArrowRight, ChevronDown, LoaderCircle, Sun, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { formatCapturedTime, humanize, isEmptyValue } from "../lib/format";
import { typeLabel, typeStyle } from "../lib/noteTypes";
import FieldValue from "./FieldValue";
import TypeIcon from "./TypeIcon";

function todayHeading() {
  return new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" }).format(
    new Date(),
  );
}

function countByType(notes) {
  const counts = new Map();
  for (const note of notes) counts.set(note.type_name, (counts.get(note.type_name) || 0) + 1);
  return [...counts.entries()];
}

function TypeCounts({ notes }) {
  return (
    <ul aria-label="Notes by type" className="flex flex-wrap gap-1.5">
      {countByType(notes).map(([typeName, count]) => {
        const { icon: Icon, chip } = typeStyle(typeName);
        return (
          <li
            key={typeName}
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${chip}`}
          >
            <Icon size={12} aria-hidden="true" />
            {count} {typeLabel(typeName)}
          </li>
        );
      })}
    </ul>
  );
}

function TodayNoteItem({ note, typeDef, isNew }) {
  const [open, setOpen] = useState(false);
  const detailsId = `today-${note.id}`;
  const fields = (typeDef?.fields || []).filter((f) => !isEmptyValue(note.fields?.[f.name]));

  return (
    <li
      className={`rounded-xl border transition ${
        isNew
          ? "animate-rise border-accent/30 bg-accent/10"
          : open
            ? "border-white/8 bg-white/4"
            : "border-transparent hover:bg-white/4"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={detailsId}
        className="flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left outline-none focus-visible:ring-4 focus-visible:ring-accent/30"
      >
        <TypeIcon typeName={note.type_name} size="sm" />
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 text-sm font-medium leading-snug text-slate-100">
            {note.summary || "Untitled note"}
          </span>
          <span className="mt-1 block text-xs text-slate-500">
            {typeLabel(note.type_name)} ·{" "}
            <time dateTime={note.created_at}>{formatCapturedTime(note.created_at, note.timezone)}</time>
          </span>
        </span>
        <ChevronDown
          size={15}
          className={`mt-0.5 shrink-0 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div id={detailsId} className="animate-fade-in space-y-3 px-3 pb-3.5 pl-14">
          {fields.length > 0 && (
            <dl className="space-y-1.5 text-xs">
              {fields.map((f) => (
                <div key={f.name} className="flex gap-2">
                  <dt className="w-16 shrink-0 text-slate-500">{humanize(f.name)}</dt>
                  <dd className="min-w-0 font-medium text-slate-200">
                    <FieldValue fieldType={f.field_type} value={note.fields[f.name]} />
                  </dd>
                </div>
              ))}
            </dl>
          )}
          <p className="border-l-2 border-accent/30 pl-2.5 text-xs italic leading-relaxed text-slate-400">
            {note.transcript}
          </p>
        </div>
      )}
    </li>
  );
}

function PanelBody({ notes, status, types, newNoteId }) {
  const typeByName = Object.fromEntries(types.map((t) => [t.name, t]));

  if (status === "loading") {
    return (
      <p className="flex items-center gap-2 px-3 py-8 text-sm text-slate-500">
        <LoaderCircle size={15} className="animate-spin" aria-hidden="true" />
        Loading…
      </p>
    );
  }
  if (status === "error") {
    return <p className="px-3 py-8 text-sm text-slate-500">Couldn’t load today’s notes.</p>;
  }
  if (notes.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/5 text-slate-500">
          <Sun size={20} aria-hidden="true" />
        </span>
        <p className="mt-1 text-sm font-medium text-slate-300">Nothing yet today</p>
        <p className="text-xs leading-relaxed text-slate-500">
          Notes you save today will collect here.
        </p>
      </div>
    );
  }
  return (
    <ul className="space-y-1">
      {notes.map((note) => (
        <TodayNoteItem
          key={note.id}
          note={note}
          typeDef={typeByName[note.type_name]}
          isNew={note.id === newNoteId}
        />
      ))}
    </ul>
  );
}

export default function TodayPanel({ headingId, notes, status, types, newNoteId, onClose }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="space-y-3 border-b border-white/6 px-5 pb-4 pt-5">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 id={headingId} className="font-display text-xl font-semibold text-white">
              Today
            </h2>
            <p className="text-xs text-slate-500">{todayHeading()}</p>
          </div>
          {onClose ? (
            <button type="button" onClick={onClose} aria-label="Close" className="btn-ghost -mr-2 p-2">
              <X size={18} aria-hidden="true" />
            </button>
          ) : (
            status === "ready" && (
              <span className="rounded-full bg-white/6 px-2.5 py-0.5 text-xs font-medium text-slate-300 tabular-nums">
                {notes.length}
              </span>
            )
          )}
        </div>
        {status === "ready" && notes.length > 0 && <TypeCounts notes={notes} />}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        <PanelBody notes={notes} status={status} types={types} newNoteId={newNoteId} />
      </div>

      <footer className="border-t border-white/6 p-2">
        <Link to="/notes" className="btn-ghost w-full justify-between px-3 text-xs text-slate-400">
          All notes
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </footer>
    </div>
  );
}
