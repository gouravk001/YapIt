const CURRENCY_LOCALES = { INR: "en-IN" };

export const CURRENCIES = ["INR", "USD", "EUR", "GBP"];

export function humanize(value) {
  const text = String(value).replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatMoney(money) {
  if (!money || money.amount === "" || money.amount == null) return null;
  const currency = money.currency || "INR";
  try {
    return new Intl.NumberFormat(CURRENCY_LOCALES[currency], {
      style: "currency",
      currency,
      maximumFractionDigits: Number.isInteger(Number(money.amount)) ? 0 : 2,
    }).format(Number(money.amount));
  } catch {
    return `${money.amount} ${currency}`;
  }
}

// Resolved dates are calendar days (YYYY-MM-DD); parse them as local dates, not UTC.
function parseCalendarDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function formatCalendarDate(isoDate) {
  if (!isoDate) return null;
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(parseCalendarDate(isoDate));
}

export function formatCapturedTime(isoString, timeZone) {
  try {
    return new Intl.DateTimeFormat(undefined, { timeStyle: "short", timeZone }).format(
      new Date(isoString),
    );
  } catch {
    return "";
  }
}

export function formatCapturedDateTime(isoString, timeZone) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone,
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function dayLabel(isoString) {
  const day = startOfDay(new Date(isoString));
  const today = startOfDay(new Date());
  const daysAgo = Math.round((today - day) / 86_400_000);
  if (daysAgo === 0) return "Today";
  if (daysAgo === 1) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: day.getFullYear() === today.getFullYear() ? undefined : "numeric",
  }).format(day);
}

export function groupByDay(notes) {
  const groups = [];
  for (const note of notes) {
    const label = dayLabel(note.created_at);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.notes.push(note);
    else groups.push({ label, notes: [note] });
  }
  return groups;
}

export function isEmptyValue(value) {
  if (value == null || value === "") return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object" && "resolved" in value) return !value.resolved && !value.spoken;
  if (typeof value === "object" && "amount" in value) return value.amount === "" || value.amount == null;
  return false;
}
