import { useState } from "react";

export default function ReviewForm({
  draft,
  types = [],
  onConfirm,
  onDiscard,
  onRetype,
  isRetyping = false,
}) {
  const [prevDraft, setPrevDraft] = useState(draft);
  const [fields, setFields] = useState(draft?.fields || {});
  const [summary, setSummary] = useState(draft?.summary || "");
  const [selectedType, setSelectedType] = useState(draft?.type_name || "general");

  if (draft !== prevDraft) {
    setPrevDraft(draft);
    setFields(draft?.fields || {});
    setSummary(draft?.summary || "");
    setSelectedType(draft?.type_name || "general");
  }

  const currentTypeDef = types.find((t) => t.name === selectedType) || {
    name: selectedType,
    fields: [],
  };

  const handleFieldChange = (fieldName, value) => {
    setFields((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const handleTypeChange = (e) => {
    const newType = e.target.value;
    setSelectedType(newType);
    if (onRetype && newType !== draft?.type_name) {
      onRetype(newType);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const updated = {
      ...draft,
      type_name: selectedType,
      type_version: currentTypeDef.version || draft.type_version || 1,
      summary: summary.trim() || draft.summary,
      fields,
      status: "confirmed",
      missing_fields: [],
    };
    onConfirm(updated);
  };

  const isMissing = (fieldName) => {
    return draft?.missing_fields?.includes(fieldName);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-xl bg-slate-900/90 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 sm:p-8 flex flex-col gap-6 shadow-2xl animate-fadeIn text-left text-white"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <span className="text-xs uppercase tracking-widest text-indigo-400 font-semibold">
            Review Note
          </span>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Check & Edit Draft
          </h2>
        </div>

        {/* Type selector */}
        <div className="flex flex-col items-end">
          <label htmlFor="note-type" className="text-[11px] text-slate-400 mb-1">
            Note Type
          </label>
          <select
            id="note-type"
            value={selectedType}
            onChange={handleTypeChange}
            disabled={isRetyping}
            className="bg-slate-800 border border-white/15 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium cursor-pointer"
          >
            {types.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isRetyping && (
        <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 flex items-center justify-center gap-2">
          <span className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          Retyping note fields...
        </div>
      )}

      {/* Spoken Transcript preview */}
      <div className="bg-black/25 p-3.5 rounded-2xl border border-white/5 space-y-1">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
          Transcript
        </span>
        <p className="text-sm text-slate-200 italic leading-relaxed">
          "{draft?.transcript}"
        </p>
      </div>

      {/* Summary field */}
      <div className="space-y-1.5">
        <label htmlFor="note-summary" className="text-xs font-semibold text-slate-300">
          Summary
        </label>
        <input
          id="note-summary"
          type="text"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          required
          className="w-full bg-slate-800/80 border border-white/15 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Dynamic Fields */}
      <div className="space-y-4 pt-2 border-t border-white/10">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
          Structured Fields
        </span>

        {currentTypeDef.fields.map((f) => {
          const val = fields[f.name];
          const missing = isMissing(f.name);

          return (
            <div key={f.name} className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor={`field-${f.name}`}
                  className="text-xs font-medium text-slate-200 capitalize flex items-center gap-1.5"
                >
                  {f.name.replace(/_/g, " ")}
                  {f.required && <span className="text-red-400">*</span>}
                </label>
                {missing && (
                  <span className="text-[11px] text-red-400 font-medium">
                    Required field missing
                  </span>
                )}
              </div>

              {/* Enum Field */}
              {f.field_type === "enum" && (
                <select
                  id={`field-${f.name}`}
                  value={val || ""}
                  onChange={(e) => handleFieldChange(f.name, e.target.value)}
                  className={`w-full bg-slate-800/80 border rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 ${
                    missing ? "border-red-500 focus:ring-red-500" : "border-white/15 focus:ring-indigo-500"
                  }`}
                >
                  <option value="">Select an option</option>
                  {(f.allowed_values || []).map((opt) => (
                    <option key={opt} value={opt}>
                      {opt.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              )}

              {/* Money Field */}
              {f.field_type === "money" && (
                <div className="flex gap-2">
                  <input
                    id={`field-${f.name}`}
                    type="number"
                    step="any"
                    placeholder="Amount"
                    value={typeof val === "object" ? val?.amount ?? "" : val ?? ""}
                    onChange={(e) => {
                      const num = e.target.value === "" ? "" : parseFloat(e.target.value);
                      const currentCurr = typeof val === "object" ? val?.currency || "INR" : "INR";
                      handleFieldChange(f.name, { amount: num, currency: currentCurr });
                    }}
                    className={`flex-1 bg-slate-800/80 border rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 ${
                      missing ? "border-red-500 focus:ring-red-500" : "border-white/15 focus:ring-indigo-500"
                    }`}
                  />
                  <select
                    value={typeof val === "object" ? val?.currency || "INR" : "INR"}
                    onChange={(e) => {
                      const currentAmt = typeof val === "object" ? val?.amount ?? 0 : val ?? 0;
                      handleFieldChange(f.name, { amount: currentAmt, currency: e.target.value });
                    }}
                    className="w-24 bg-slate-800 border border-white/15 rounded-xl px-2 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
              )}

              {/* Date Field */}
              {f.field_type === "date" && (
                <div className="space-y-1">
                  <input
                    id={`field-${f.name}`}
                    type="date"
                    value={
                      typeof val === "object"
                        ? val?.resolved || ""
                        : typeof val === "string" && val.match(/^\d{4}-\d{2}-\d{2}$/)
                        ? val
                        : ""
                    }
                    onChange={(e) => {
                      const spoken = typeof val === "object" ? val?.spoken || "" : "";
                      handleFieldChange(f.name, { spoken, resolved: e.target.value });
                    }}
                    className={`w-full bg-slate-800/80 border rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 ${
                      missing ? "border-red-500 focus:ring-red-500" : "border-white/15 focus:ring-indigo-500"
                    }`}
                  />
                  {typeof val === "object" && val?.spoken && (
                    <span className="text-[11px] text-slate-400 block">
                      Spoken phrase: <span className="italic text-slate-300">"{val.spoken}"</span>
                    </span>
                  )}
                </div>
              )}

              {/* Number Field */}
              {f.field_type === "number" && (
                <input
                  id={`field-${f.name}`}
                  type="number"
                  step="any"
                  value={val ?? ""}
                  onChange={(e) =>
                    handleFieldChange(
                      f.name,
                      e.target.value === "" ? "" : parseFloat(e.target.value)
                    )
                  }
                  className={`w-full bg-slate-800/80 border rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 ${
                    missing ? "border-red-500 focus:ring-red-500" : "border-white/15 focus:ring-indigo-500"
                  }`}
                />
              )}

              {/* List Field */}
              {f.field_type === "list" && (
                <input
                  id={`field-${f.name}`}
                  type="text"
                  placeholder="Comma-separated items"
                  value={Array.isArray(val) ? val.join(", ") : val || ""}
                  onChange={(e) =>
                    handleFieldChange(
                      f.name,
                      e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean)
                    )
                  }
                  className="w-full bg-slate-800/80 border border-white/15 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              )}

              {/* Text and Person Field */}
              {(f.field_type === "text" || f.field_type === "person") && (
                <input
                  id={`field-${f.name}`}
                  type="text"
                  value={val ?? ""}
                  onChange={(e) => handleFieldChange(f.name, e.target.value)}
                  className={`w-full bg-slate-800/80 border rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 ${
                    missing ? "border-red-500 focus:ring-red-500" : "border-white/15 focus:ring-indigo-500"
                  }`}
                />
              )}

              <p className="text-[11px] text-slate-400">{f.description}</p>
            </div>
          );
        })}
      </div>

      {/* Form Action Buttons */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
        <button
          type="button"
          onClick={onDiscard}
          className="px-5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 text-sm font-semibold transition cursor-pointer"
        >
          Discard
        </button>

        <button
          type="submit"
          disabled={isRetyping}
          className="px-6 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-sm font-semibold shadow-lg shadow-indigo-500/25 transition cursor-pointer"
        >
          Confirm & Save Note
        </button>
      </div>
    </form>
  );
}
