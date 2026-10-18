import { typeLabel, typeStyle } from "../lib/noteTypes";

export default function TypePicker({ types, value, onChange, disabled }) {
  return (
    <div role="radiogroup" aria-label="Note type" className="flex flex-wrap gap-2">
      {types.map((t) => {
        const { icon: Icon, chip } = typeStyle(t.name);
        const selected = t.name === value;
        return (
          <button
            key={t.name}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => !selected && onChange(t.name)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition outline-none focus-visible:ring-4 focus-visible:ring-accent/30 disabled:cursor-wait ${
              selected
                ? chip
                : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200"
            }`}
          >
            <Icon size={14} aria-hidden="true" />
            {typeLabel(t.name)}
          </button>
        );
      })}
    </div>
  );
}
