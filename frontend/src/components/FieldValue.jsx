import { formatCalendarDate, formatMoney, humanize } from "../lib/format";

function DateValue({ value }) {
  const formatted = formatCalendarDate(value.resolved);
  return (
    <span>
      {formatted || <span className="text-amber-300">Unresolved</span>}
      {value.spoken && (
        <span className="ml-1.5 text-xs font-normal text-slate-500">“{value.spoken}”</span>
      )}
    </span>
  );
}

export default function FieldValue({ fieldType, value }) {
  if (fieldType === "date" || (typeof value === "object" && value && "resolved" in value)) {
    return <DateValue value={value} />;
  }
  if (fieldType === "money" || (typeof value === "object" && value && "amount" in value)) {
    return <span className="tabular-nums">{formatMoney(value)}</span>;
  }
  if (fieldType === "enum") return humanize(value);
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}
