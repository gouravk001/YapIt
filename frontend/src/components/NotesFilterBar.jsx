import { Search, User, X } from "lucide-react";
import { typeLabel, typeStyle } from "../lib/noteTypes";

function ClearButton({ label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-500 hover:text-white"
    >
      <X size={14} aria-hidden="true" />
    </button>
  );
}

function TypeChip({ selected, onClick, children, chipClass }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition outline-none focus-visible:ring-4 focus-visible:ring-accent/30 ${
        selected ? chipClass : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

export default function NotesFilterBar({ types, filters, onChange }) {
  const set = (key) => (value) => onChange({ ...filters, [key]: value });

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true" />
          <input
            type="search"
            aria-label="Search notes"
            placeholder="Search notes…"
            value={filters.search}
            onChange={(e) => set("search")(e.target.value)}
            className="field-input pl-10 pr-9"
          />
          {filters.search && <ClearButton label="Clear search" onClick={() => set("search")("")} />}
        </div>
        <div className="relative sm:w-52">
          <User size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true" />
          <input
            type="text"
            aria-label="Filter by person"
            placeholder="Person"
            value={filters.person}
            onChange={(e) => set("person")(e.target.value)}
            className="field-input pl-10 pr-9"
          />
          {filters.person && <ClearButton label="Clear person filter" onClick={() => set("person")("")} />}
        </div>
      </div>

      <div role="group" aria-label="Filter by type" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
        <TypeChip
          selected={!filters.type}
          onClick={() => set("type")("")}
          chipClass="border-white/30 bg-white/10 text-white"
        >
          All
        </TypeChip>
        {types.map((t) => {
          const { icon: Icon, chip } = typeStyle(t.name);
          return (
            <TypeChip
              key={t.name}
              selected={filters.type === t.name}
              onClick={() => set("type")(filters.type === t.name ? "" : t.name)}
              chipClass={chip}
            >
              <Icon size={14} aria-hidden="true" />
              {typeLabel(t.name)}
            </TypeChip>
          );
        })}
      </div>
    </div>
  );
}
