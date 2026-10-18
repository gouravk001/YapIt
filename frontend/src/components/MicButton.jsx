import { LoaderCircle, Mic } from "lucide-react";

export default function MicButton({ isRecording, isBusy, onClick }) {
  const label = isRecording ? "Stop recording" : "Start recording";
  return (
    <div className="relative flex h-40 w-40 items-center justify-center">
      {isRecording && (
        <>
          <span className="absolute h-28 w-28 animate-ring rounded-full bg-red-400/40" aria-hidden="true" />
          <span
            className="absolute h-28 w-28 animate-ring rounded-full bg-red-400/30 [animation-delay:0.9s]"
            aria-hidden="true"
          />
        </>
      )}
      <button
        type="button"
        onClick={onClick}
        disabled={isBusy}
        aria-label={label}
        aria-pressed={isRecording}
        className={`relative flex h-28 w-28 items-center justify-center rounded-full bg-white text-ink-950 shadow-[0_10px_40px_-8px_rgb(156_195_255/0.45)] transition duration-300 outline-none focus-visible:ring-8 focus-visible:ring-accent/30 disabled:cursor-wait ${
          isRecording ? "scale-95 shadow-[0_10px_50px_-6px_rgb(248_113_113/0.6)]" : "hover:scale-105 active:scale-95"
        }`}
      >
        {isBusy ? (
          <LoaderCircle size={36} className="animate-spin text-slate-400" aria-hidden="true" />
        ) : isRecording ? (
          <span className="h-9 w-9 rounded-lg bg-red-500" aria-hidden="true" />
        ) : (
          <Mic size={40} strokeWidth={2} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}
