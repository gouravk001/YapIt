import { useState } from "react";

const TYPE_COLORS = {
  payment: "bg-emerald-500/15 border-emerald-500/30 text-emerald-300",
  promise: "bg-amber-500/15 border-amber-500/30 text-amber-300",
  event: "bg-blue-500/15 border-blue-500/30 text-blue-300",
  info: "bg-purple-500/15 border-purple-500/30 text-purple-300",
  general: "bg-slate-500/15 border-slate-500/30 text-slate-300",
};

export default function NoteCard({ note, onDelete, onEdit }) {
  const [expanded, setExpanded] = useState(false);

  const typeClass =
    TYPE_COLORS[note.type_name] || "bg-indigo-500/15 border-indigo-500/30 text-indigo-300";

  const formatDate = (isoString, tz) => {
    try {
      return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: tz || undefined,
      }).format(new Date(isoString));
    } catch {
      return isoString;
    }
  };

  const renderFieldValue = (val) => {
    if (val === null || val === undefined) return "—";

    // Date object {spoken, resolved}
    if (typeof val === "object" && ("resolved" in val || "spoken" in val)) {
      const res = val.resolved || "unresolved";
      const spk = val.spoken ? ` ("${val.spoken}")` : "";
      return `${res}${spk}`;
    }

    // Money object {amount, currency}
    if (typeof val === "object" && "amount" in val) {
      const curr = val.currency || "INR";
      const sym = curr === "INR" ? "₹" : curr === "USD" ? "$" : curr === "EUR" ? "€" : curr === "GBP" ? "£" : "";
      return `${sym}${val.amount} ${curr}`;
    }

    // List
    if (Array.isArray(val)) {
      return val.join(", ");
    }

    if (typeof val === "boolean") {
      return val ? "Yes" : "No";
    }

    return String(val);
  };

  const hasMissing = note.missing_fields && note.missing_fields.length > 0;

  return (
    <article className="rounded-2xl bg-white/[0.04] backdrop-blur-md border border-white/10 p-5 hover:border-white/20 transition-all flex flex-col gap-3 shadow-lg">
      {/* Header: Type Badge, Created At, Missing Warning */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${typeClass}`}
          >
            {note.type_name}
          </span>

          {hasMissing && (
            <span className="text-[11px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
              <span>⚠</span> Needs attention
            </span>
          )}
        </div>

        <span className="text-xs text-slate-400">
          {formatDate(note.created_at, note.timezone)}
        </span>
      </div>

      {/* Summary */}
      <h3 className="text-lg font-bold text-white tracking-tight">
        {note.summary || "Voice Note"}
      </h3>

      {/* Key Fields */}
      <div className="flex flex-wrap gap-2 pt-1">
        {Object.entries(note.fields || {}).map(([key, value]) => {
          if (value === null || value === undefined || value === "") return null;
          return (
            <div
              key={key}
              className="text-xs bg-white/5 border border-white/10 rounded-lg px-2.5 py-1 text-slate-300 flex items-center gap-1.5"
            >
              <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}:</span>
              <span className="font-semibold text-slate-100">{renderFieldValue(value)}</span>
            </div>
          );
        })}
      </div>

      {/* Transcript collapsible */}
      {expanded && (
        <div className="mt-2 pt-3 border-t border-white/10 text-xs text-slate-300 space-y-2 animate-fadeIn">
          <div>
            <span className="text-slate-400 font-semibold block mb-0.5">Spoken Transcript:</span>
            <p className="italic text-slate-200 bg-black/20 p-2.5 rounded-lg border border-white/5">
              "{note.transcript}"
            </p>
          </div>
          {hasMissing && (
            <p className="text-amber-400/90 text-[11px]">
              Missing or incomplete required fields: {note.missing_fields.join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between text-xs">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-indigo-400 hover:text-indigo-300 font-medium transition cursor-pointer"
        >
          {expanded ? "Show less" : "View transcript"}
        </button>

        <div className="flex items-center gap-2">
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(note)}
              className="px-3 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 font-medium transition cursor-pointer"
            >
              Edit
            </button>
          )}

          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(note.id)}
              className="px-3 py-1 rounded-lg bg-red-600/20 hover:bg-red-600/40 text-red-300 border border-red-500/30 font-medium transition cursor-pointer"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

