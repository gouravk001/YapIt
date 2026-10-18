import { Check } from "lucide-react";
import { STEP_LABELS } from "../lib/pipelineSteps";

export default function ProgressSteps({ steps, current }) {
  const currentIndex = Math.max(0, steps.indexOf(current));

  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center gap-2">
      <ol aria-label="Progress" className="flex items-center">
        {steps.map((step, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          return (
            <li key={step} className="flex items-center">
              {i > 0 && (
                <span
                  aria-hidden="true"
                  className={`h-px w-6 transition-colors sm:w-9 ${done || active ? "bg-accent/60" : "bg-white/10"}`}
                />
              )}
              <span
                className={`flex h-4 w-4 items-center justify-center rounded-full transition ${
                  done
                    ? "bg-accent text-ink-950"
                    : active
                      ? "bg-accent/20 ring-2 ring-accent animate-pulse"
                      : "bg-white/10"
                }`}
              >
                {done && <Check size={10} strokeWidth={3} aria-hidden="true" />}
              </span>
              <span className="sr-only">
                {STEP_LABELS[step]}: {done ? "done" : active ? "in progress" : "waiting"}
              </span>
            </li>
          );
        })}
      </ol>
      <p aria-hidden="true" className="text-sm font-medium text-slate-300">
        {STEP_LABELS[steps[currentIndex]]}…
      </p>
    </div>
  );
}
