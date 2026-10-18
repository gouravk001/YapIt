import { CalendarCheck, Keyboard, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getTypes, processAudio, processText, retypeNote, saveNote } from "../api/client";
import Banner from "../components/Banner";
import Drawer from "../components/Drawer";
import MicButton from "../components/MicButton";
import ProgressSteps from "../components/ProgressSteps";
import RejectionNotice from "../components/RejectionNotice";
import ReviewForm from "../components/ReviewForm";
import TextNoteForm from "../components/TextNoteForm";
import TodayPanel from "../components/TodayPanel";
import WaveformBars from "../components/WaveformBars";
import { LIMIT_WARNING_SECONDS, MAX_RECORDING_SECONDS } from "../config";
import { useRecorder } from "../hooks/useRecorder";
import { useTodayNotes } from "../hooks/useTodayNotes";
import { AUDIO_STEPS, TEXT_STEPS } from "../lib/pipelineSteps";

// Backend rejections that mean "try again", not "something broke".
const REJECTION_CODES = new Set(["UnclearAudio", "NotANote"]);
const SAVED_NOTICE_MS = 3500;

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

function formatTimer(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function isTextEntry(target) {
  return target.closest("input, textarea, select, [contenteditable='true']");
}

export default function Home() {
  const [types, setTypes] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | processing | review | rejected | error
  const [draft, setDraft] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isRetyping, setIsRetyping] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showTextInput, setShowTextInput] = useState(false);
  const [rejection, setRejection] = useState(null);
  const [savedNoteId, setSavedNoteId] = useState(null);
  const [showTodayDrawer, setShowTodayDrawer] = useState(false);
  const [todayRefresh, setTodayRefresh] = useState(0);
  const lastAttempt = useRef(null);
  const [progress, setProgress] = useState(null); // { steps, stage } while a draft streams in
  const today = useTodayNotes(todayRefresh);

  useEffect(() => {
    if (!savedNoteId) return;
    const timer = setTimeout(() => setSavedNoteId(null), SAVED_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [savedNoteId]);

  useEffect(() => {
    getTypes()
      .then((data) => setTypes(data || []))
      .catch(() => setTypes([]));
  }, []);

  const runAttempt = async (attempt) => {
    lastAttempt.current = attempt;
    setStatus("processing");
    setErrorMessage(null);
    setRejection(null);
    const steps = attempt.kind === "audio" ? AUDIO_STEPS : TEXT_STEPS;
    setProgress({ steps, stage: steps[0] });
    const onStage = (stage) => setProgress((current) => current && { ...current, stage });
    try {
      const timezone = browserTimezone();
      const result =
        attempt.kind === "audio"
          ? await processAudio(attempt.blob, attempt.capturedAt, timezone, onStage)
          : await processText(attempt.text, attempt.capturedAt, timezone, onStage);
      setDraft(result);
      setShowTextInput(false);
      setStatus("review");
    } catch (err) {
      if (REJECTION_CODES.has(err.code)) {
        setRejection({ code: err.code, message: err.message, transcript: err.transcript, attempt });
        setShowTextInput(false);
        setStatus("rejected");
        return;
      }
      setErrorMessage(err.message || "Something went wrong while processing your note.");
      setStatus("error");
    } finally {
      setProgress(null);
    }
  };

  const keepAsNote = async () => {
    setStatus("processing");
    try {
      const timezone = browserTimezone();
      setDraft(await retypeNote(rejection.transcript, "general", rejection.attempt.capturedAt, timezone));
      setRejection(null);
      setStatus("review");
    } catch (err) {
      setErrorMessage(err.message || "Couldn't save that as a note.");
      setStatus("error");
    }
  };

  const {
    isRecording,
    hitLimit,
    analyser,
    seconds,
    startRecording,
    stopRecording,
    error: micError,
  } = useRecorder(
    (blob, capturedAt) => runAttempt({ kind: "audio", blob, capturedAt }),
    MAX_RECORDING_SECONDS,
  );
  const nearLimit = seconds >= MAX_RECORDING_SECONDS - LIMIT_WARNING_SECONDS;

  const isBusy = status === "processing";

  const toggleRecording = () => {
    if (isBusy) return;
    if (isRecording) stopRecording();
    else startRecording();
  };

  useEffect(() => {
    if (status === "review") return;
    const onKeyDown = (e) => {
      // Space records from anywhere on the page, except while typing or inside a dialog.
      if (e.code !== "Space" || e.repeat || isTextEntry(e.target)) return;
      if (document.querySelector("dialog[open]")) return;
      e.preventDefault();
      // Otherwise a focused button would also be clicked when Space is released.
      if (e.target instanceof HTMLElement && e.target !== document.body) e.target.blur();
      toggleRecording();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const handleRetype = async (typeName) => {
    setIsRetyping(true);
    setErrorMessage(null);
    try {
      setDraft(await retypeNote(draft.transcript, typeName, draft.created_at, draft.timezone));
    } catch (err) {
      setErrorMessage(err.message || "Couldn't switch the note type.");
    } finally {
      setIsRetyping(false);
    }
  };

  const handleSave = async (note) => {
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await saveNote(note);
      setDraft(null);
      setStatus("idle");
      setSavedNoteId(note.id);
      setTodayRefresh((n) => n + 1);
    } catch (err) {
      setErrorMessage(err.message || "Couldn't save the note.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    setDraft(null);
    setStatus("idle");
    setErrorMessage(null);
  };

  const caption = isRecording
    ? "Listening… tap to stop"
    : isBusy
      ? "Turning that into a note…"
      : "Tap to record a note";

  const isReviewing = status === "review" && draft;

  const review = (
    <div className="mx-auto w-full max-w-2xl space-y-3 py-6 sm:py-10">
      {errorMessage && <Banner>{errorMessage}</Banner>}
      <ReviewForm
        draft={draft}
        types={types}
        onConfirm={handleSave}
        onDiscard={handleDiscard}
        onRetype={handleRetype}
        isRetyping={isRetyping}
        isSaving={isSaving}
      />
    </div>
  );

  const recorder = (
    <div className="m-auto flex w-full max-w-md flex-col items-center py-10 text-center sm:py-14">
      <h1 className="font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
        What’s on your mind?
      </h1>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-400">
        Say it out loud. YapIt writes it down, sorts it into a payment, promise, event or note, and
        lets you check it before saving.
      </p>

      <div className="mt-10 flex h-12 items-center justify-center">
        {isRecording ? (
          <WaveformBars analyser={analyser} />
        ) : (
          <p className="text-sm text-slate-500">Everything stays on this device</p>
        )}
      </div>

      <MicButton isRecording={isRecording} isBusy={isBusy} onClick={toggleRecording} />

      <div className="mt-2 flex h-14 flex-col items-center gap-1" aria-live="polite">
        {isRecording && (
          <span
            className={`flex items-center gap-2 font-mono text-sm font-medium tabular-nums ${nearLimit ? "text-amber-300" : "text-red-300"}`}
          >
            <span className="h-2 w-2 animate-pulse rounded-full bg-red-400" aria-hidden="true" />
            {formatTimer(seconds)}
            {nearLimit && ` / ${formatTimer(MAX_RECORDING_SECONDS)}`}
          </span>
        )}
        {isBusy && progress ? (
          <ProgressSteps steps={progress.steps} current={progress.stage} />
        ) : (
          <p className={`text-sm font-medium ${isRecording ? "text-red-200" : "text-slate-300"}`}>
            {caption}
          </p>
        )}
        {!isBusy && (
          <p className="hidden text-xs text-slate-500 sm:block">
            {isRecording ? "press" : "or press"} <span className="kbd">Space</span>
            {isRecording && " to stop"}
          </p>
        )}
      </div>

      <div className="mt-6 w-full space-y-3">
        {hitLimit && !isRecording && (
          <p className="text-xs text-amber-300">
            Stopped at {formatTimer(MAX_RECORDING_SECONDS)}, the limit for one note.
          </p>
        )}
        {savedNoteId && (
          <Banner tone="success">Saved to today’s notes.</Banner>
        )}
        {micError && <Banner>{micError}</Banner>}

        {status === "error" && errorMessage && (
          <Banner
            action={
              <button
                type="button"
                onClick={() => runAttempt(lastAttempt.current)}
                className="btn-subtle shrink-0 px-3 py-1.5 text-xs"
              >
                <RotateCcw size={14} aria-hidden="true" />
                Retry
              </button>
            }
          >
            {errorMessage}
          </Banner>
        )}

        {status === "rejected" && rejection && (
          <RejectionNotice
            rejection={rejection}
            busy={isBusy}
            onRecordAgain={() => {
              setRejection(null);
              setStatus("idle");
              startRecording();
            }}
            onEditText={() => {
              setStatus("idle");
              setShowTextInput(true);
            }}
            onKeepAnyway={keepAsNote}
          />
        )}

        {showTextInput ? (
          <TextNoteForm
            initialText={rejection?.attempt.kind === "text" ? rejection.attempt.text : ""}
            disabled={isBusy}
            onCancel={() => {
              setShowTextInput(false);
              setRejection(null);
            }}
            onSubmit={(text) => runAttempt({ kind: "text", text, capturedAt: new Date().toISOString() })}
          />
        ) : (
          status !== "rejected" && (
            <button
              type="button"
              onClick={() => setShowTextInput(true)}
              disabled={isBusy || isRecording}
              className="btn-ghost mx-auto text-xs text-slate-400"
            >
              <Keyboard size={15} aria-hidden="true" />
              Type a note instead
            </button>
          )
        )}
      </div>
    </div>
  );

  const panelProps = { notes: today.notes, status: today.status, types, newNoteId: savedNoteId };

  return (
    <div className="flex lg:h-[calc(100dvh-4rem)]">
      <aside
        aria-labelledby="today-heading"
        className="hidden w-80 shrink-0 border-r border-white/6 bg-ink-900/50 lg:block"
      >
        <TodayPanel headingId="today-heading" {...panelProps} />
      </aside>

      <div className="min-w-0 flex-1 p-3 sm:p-4 lg:overflow-y-auto">
        <section
          aria-label={isReviewing ? "Review note" : "Record a note"}
          className="stage flex min-h-[calc(100dvh-5rem)] flex-col px-4 sm:min-h-[calc(100dvh-6rem)] sm:px-8 lg:min-h-full"
        >
          {!isReviewing && (
            <div className="pt-4 lg:hidden">
              <button type="button" onClick={() => setShowTodayDrawer(true)} className="btn-subtle px-3 py-1.5 text-xs">
                <CalendarCheck size={15} aria-hidden="true" />
                Today
                {today.status === "ready" && (
                  <span className="rounded-full bg-white/10 px-1.5 tabular-nums">{today.notes.length}</span>
                )}
              </button>
            </div>
          )}
          {isReviewing ? review : recorder}
        </section>
      </div>

      {showTodayDrawer && (
        <Drawer label="Today’s notes" onClose={() => setShowTodayDrawer(false)}>
          <TodayPanel headingId="today-drawer-heading" {...panelProps} onClose={() => setShowTodayDrawer(false)} />
        </Drawer>
      )}
    </div>
  );
}
