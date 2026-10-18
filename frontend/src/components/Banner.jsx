import { Check, TriangleAlert } from "lucide-react";

const TONES = {
  error: { icon: TriangleAlert, box: "border-red-400/25 bg-red-500/10 text-red-200" },
  success: { icon: Check, box: "border-emerald-400/25 bg-emerald-400/10 text-emerald-100" },
};

export default function Banner({ tone = "error", children, action }) {
  const { icon: Icon, box } = TONES[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`flex w-full animate-fade-in items-start gap-3 rounded-xl border px-4 py-3 text-left text-sm ${box}`}
    >
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="flex-1">{children}</div>
      {action}
    </div>
  );
}
