import { CalendarDays, Handshake, Lightbulb, StickyNote, Wallet } from "lucide-react";

// Types are data from the backend; these only add a look for the built-in ones.
const TYPE_STYLES = {
  payment: {
    icon: Wallet,
    tile: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
    chip: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
  },
  promise: {
    icon: Handshake,
    tile: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
    chip: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  },
  event: {
    icon: CalendarDays,
    tile: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
    chip: "border-sky-400/40 bg-sky-400/10 text-sky-200",
  },
  info: {
    icon: Lightbulb,
    tile: "bg-violet-400/10 text-violet-300 ring-violet-400/20",
    chip: "border-violet-400/40 bg-violet-400/10 text-violet-200",
  },
};

const FALLBACK_STYLE = {
  icon: StickyNote,
  tile: "bg-slate-400/10 text-slate-300 ring-slate-400/20",
  chip: "border-slate-400/40 bg-slate-400/10 text-slate-200",
};

export function typeStyle(typeName) {
  return TYPE_STYLES[typeName] || FALLBACK_STYLE;
}

export function typeLabel(typeName) {
  if (!typeName) return "Note";
  return typeName.charAt(0).toUpperCase() + typeName.slice(1).replace(/_/g, " ");
}
