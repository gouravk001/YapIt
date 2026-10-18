import { CURRENCIES, formatMoney, humanize } from "../lib/format";

const SEGMENTED_MAX_OPTIONS = 3;

function inputClass(missing) {
  return `field-input ${missing ? "field-input-missing" : ""}`;
}

function EnumInput({ id, field, value, onChange, missing }) {
  const options = field.allowed_values || [];
  if (options.length > SEGMENTED_MAX_OPTIONS) {
    return (
      <select id={id} value={value || ""} onChange={(e) => onChange(e.target.value)} className={inputClass(missing)}>
        <option value="">Choose…</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {humanize(opt)}
          </option>
        ))}
      </select>
    );
  }
  return (
    <div
      id={id}
      role="radiogroup"
      aria-labelledby={`${id}-label`}
      className={`grid gap-1 rounded-xl border p-1 ${missing ? "border-amber-400/60 bg-amber-400/5" : "border-white/10 bg-ink-900/80"}`}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          role="radio"
          aria-checked={value === opt}
          onClick={() => onChange(opt)}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium transition outline-none focus-visible:ring-4 focus-visible:ring-accent/30 ${
            value === opt ? "bg-white text-ink-950 shadow" : "text-slate-400 hover:text-white"
          }`}
        >
          {humanize(opt)}
        </button>
      ))}
    </div>
  );
}

function MoneyInput({ id, value, onChange, missing }) {
  const money = value && typeof value === "object" ? value : { amount: "", currency: "INR" };
  const preview = formatMoney(money);
  return (
    <div>
      <div className="flex gap-2">
        <select
          aria-label="Currency"
          value={money.currency || "INR"}
          onChange={(e) => onChange({ ...money, currency: e.target.value })}
          className="field-input w-24 shrink-0 px-2.5"
        >
          {CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          id={id}
          type="number"
          inputMode="decimal"
          step="any"
          min="0"
          placeholder="0"
          value={money.amount ?? ""}
          onChange={(e) => onChange({ ...money, amount: e.target.value === "" ? "" : Number(e.target.value) })}
          className={`${inputClass(missing)} tabular-nums`}
        />
      </div>
      {preview && <p className="mt-1.5 text-xs text-slate-400 tabular-nums">{preview}</p>}
    </div>
  );
}

function DateInput({ id, value, onChange, missing }) {
  const date = value && typeof value === "object" ? value : { spoken: "", resolved: "" };
  return (
    <div>
      <input
        id={id}
        type="date"
        value={date.resolved || ""}
        onChange={(e) => onChange({ ...date, resolved: e.target.value })}
        className={inputClass(missing)}
      />
      {date.spoken && (
        <p className="mt-1.5 text-xs text-slate-400">
          Heard <span className="text-slate-300">“{date.spoken}”</span>
        </p>
      )}
    </div>
  );
}

function ListInput({ id, field, value, onChange, missing }) {
  return (
    <input
      id={id}
      type="text"
      placeholder={field.description}
      value={Array.isArray(value) ? value.join(", ") : value || ""}
      onChange={(e) =>
        onChange(
          e.target.value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        )
      }
      className={inputClass(missing)}
    />
  );
}

function TextInput({ id, field, value, onChange, missing, type = "text" }) {
  return (
    <input
      id={id}
      type={type}
      step={type === "number" ? "any" : undefined}
      placeholder={field.description}
      value={value ?? ""}
      onChange={(e) =>
        onChange(type === "number" && e.target.value !== "" ? Number(e.target.value) : e.target.value)
      }
      className={inputClass(missing)}
    />
  );
}

const INPUTS = {
  enum: EnumInput,
  money: MoneyInput,
  date: DateInput,
  list: ListInput,
  number: (props) => <TextInput {...props} type="number" />,
};

function isWideField(field) {
  return field.field_type === "text" || field.field_type === "list";
}

export default function FieldInput({ field, value, onChange, missing, warning }) {
  const flagged = missing || Boolean(warning);
  const id = `field-${field.name}`;
  const Input = INPUTS[field.field_type] || TextInput;
  return (
    <div className={isWideField(field) ? "sm:col-span-2" : ""}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label id={`${id}-label`} htmlFor={id} className="text-xs font-medium text-slate-300">
          {humanize(field.name)}
          {field.required && (
            <span className="ml-0.5 text-slate-500" aria-label="required">
              *
            </span>
          )}
        </label>
        {missing ? (
          <span className="text-[11px] font-medium text-amber-300">Needs a value</span>
        ) : (
          warning && <span className="text-[11px] font-medium text-amber-300">Check this</span>
        )}
      </div>
      <Input id={id} field={field} value={value} onChange={onChange} missing={flagged} />
    </div>
  );
}
