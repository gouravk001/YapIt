import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import microphone from "../assets/microphone.png";
import WaveformBars from "../components/WaveformBars";
import ReviewForm from "../components/ReviewForm";
import { useRecorder } from "../hooks/useRecorder";
import { getTypes, processAudio, processText, retypeNote, saveNote } from "../api/client";

export default function Home() {
  const navigate = useNavigate();
  const [types, setTypes] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | processing | review | error
  const [draft, setDraft] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isRetyping, setIsRetyping] = useState(false);
  const [lastAudio, setLastAudio] = useState(null);
  const [pastedText, setPastedText] = useState("");
  const [showTextInput, setShowTextInput] = useState(false);

  // Load types once on mount
  useEffect(() => {
    getTypes()
      .then((data) => setTypes(data || []))
      .catch((err) => console.error("Could not fetch note types:", err));
  }, []);

  const getTimezone = () => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    } catch {
      return "UTC";
    }
  };

  const submitAudio = async (blob, capturedAt) => {
    setStatus("processing");
    setErrorMessage(null);
    try {
      const tz = getTimezone();
      const result = await processAudio(blob, capturedAt, tz);
      setDraft(result);
      setStatus("review");
    } catch (err) {
      console.error("Audio processing error:", err);
      setErrorMessage(err.message || "Failed to process audio.");
      setStatus("error");
    }
  };

  const handleAudioFinished = async (blob, capturedAt) => {
    setLastAudio({ blob, capturedAt });
    await submitAudio(blob, capturedAt);
  };

  const {
    isRecording,
    analyser,
    seconds,
    startRecording,
    stopRecording,
    error: micError,
  } = useRecorder(handleAudioFinished);

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!pastedText.trim()) return;

    setStatus("processing");
    setErrorMessage(null);
    try {
      const capturedAt = new Date().toISOString();
      const tz = getTimezone();
      const result = await processText(pastedText.trim(), capturedAt, tz);
      setDraft(result);
      setStatus("review");
      setPastedText("");
      setShowTextInput(false);
    } catch (err) {
      console.error("Text processing error:", err);
      setErrorMessage(err.message || "Failed to process text.");
      setStatus("error");
    }
  };

  const handleRetype = async (newTypeName) => {
    if (!draft) return;
    setIsRetyping(true);
    try {
      const tz = getTimezone();
      const updatedDraft = await retypeNote(
        draft.transcript,
        newTypeName,
        draft.created_at,
        tz
      );
      setDraft(updatedDraft);
    } catch (err) {
      console.error("Retype error:", err);
      setErrorMessage("Failed to change note type.");
    } finally {
      setIsRetyping(false);
    }
  };

  const handleConfirmSave = async (confirmedEnvelope) => {
    setStatus("processing");
    try {
      await saveNote(confirmedEnvelope);
      navigate("/notes");
    } catch (err) {
      console.error("Save note error:", err);
      setErrorMessage(err.message || "Failed to save note.");
      setStatus("review");
    }
  };

  const handleDiscard = () => {
    setDraft(null);
    setLastAudio(null);
    setStatus("idle");
    setErrorMessage(null);
  };

  const handleRetry = () => {
    if (lastAudio) {
      submitAudio(lastAudio.blob, lastAudio.capturedAt);
    } else {
      setStatus("idle");
    }
  };

  const handleMicClick = () => {
    if (status === "processing") return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const formatTimer = (s) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] bg-[#080c18] flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden text-center text-white">
      {/* Ambient background glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-indigo-700/15 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full bg-purple-700/15 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-xl mx-auto flex flex-col items-center">
        {/* Review Mode */}
        {status === "review" && draft && (
          <ReviewForm
            draft={draft}
            types={types}
            onConfirm={handleConfirmSave}
            onDiscard={handleDiscard}
            onRetype={handleRetype}
            isRetyping={isRetyping}
          />
        )}

        {/* Recording / Idle / Processing Mode */}
        {status !== "review" && (
          <>
            {/* Wordmark */}
            <span className="mb-3 text-xs font-semibold tracking-[0.25em] uppercase text-indigo-400">
              YapIt Voice Notes
            </span>
            <h1 className="text-4xl sm:text-6xl font-extrabold text-white leading-tight tracking-tight">
              Speak your <br />
              <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                thoughts.
              </span>
            </h1>
            <p className="mt-3 text-slate-400 text-sm max-w-sm">
              Tap the mic, speak your note in plain English, and let YapIt transcribe and organize it locally.
            </p>

            {/* Main Interactive Card */}
            <div className="mt-8 w-full max-w-md rounded-3xl bg-white/[0.04] backdrop-blur-xl border border-white/10 p-8 flex flex-col items-center gap-6 shadow-2xl">
              {/* Waveform / Status visual */}
              <div className="w-full flex items-center justify-center min-h-[72px]">
                {isRecording ? (
                  <WaveformBars analyser={analyser} />
                ) : status === "processing" ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-400 animate-spin" />
                    <span className="text-xs text-indigo-300 font-medium animate-pulse">
                      Processing audio with Gemma...
                    </span>
                  </div>
                ) : (
                  <div className="w-14 h-14 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-500" />
                  </div>
                )}
              </div>

              {/* Timer when recording */}
              {isRecording && (
                <div className="flex items-center gap-2 text-red-400 text-sm font-mono font-semibold">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                  {formatTimer(seconds)}
                </div>
              )}

              {/* Central Mic Button */}
              <button
                type="button"
                onClick={handleMicClick}
                disabled={status === "processing"}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                className={`relative w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/40 cursor-pointer ${
                  status === "processing"
                    ? "bg-slate-800 opacity-60 cursor-wait"
                    : isRecording
                    ? "bg-red-600 hover:bg-red-500 shadow-[0_0_40px_rgba(239,68,68,0.5)] scale-105"
                    : "bg-gradient-to-br from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 shadow-[0_0_40px_rgba(99,102,241,0.4)] hover:scale-105"
                }`}
              >
                {isRecording && (
                  <span className="absolute inset-0 rounded-full bg-red-500/30 animate-ping pointer-events-none" />
                )}

                {isRecording ? (
                  <span className="w-9 h-9 rounded-md bg-white shadow-sm" />
                ) : (
                  <img
                    src={microphone}
                    alt="Microphone"
                    className="w-12 h-12 object-contain"
                  />
                )}
              </button>

              {/* Status caption */}
              <p
                className={`text-sm font-medium transition-colors ${
                  isRecording
                    ? "text-red-400"
                    : status === "processing"
                    ? "text-indigo-400"
                    : "text-slate-400"
                }`}
              >
                {isRecording
                  ? "Listening... tap to stop"
                  : status === "processing"
                  ? "Extracting note fields..."
                  : "Tap the mic to start yapping"}
              </p>

              {/* Microphone access error */}
              {micError && (
                <p className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2 text-left">
                  {micError}
                </p>
              )}

              {/* Backend Error State with Retry */}
              {status === "error" && errorMessage && (
                <div className="w-full flex flex-col items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                  <p>{errorMessage}</p>
                  <button
                    type="button"
                    onClick={handleRetry}
                    className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition"
                  >
                    Retry previous recording
                  </button>
                </div>
              )}
            </div>

            {/* Text input alternative */}
            <div className="mt-6">
              {!showTextInput ? (
                <button
                  type="button"
                  onClick={() => setShowTextInput(true)}
                  className="text-xs text-slate-500 hover:text-slate-300 transition underline underline-offset-4 cursor-pointer"
                >
                  Or paste a transcript as text
                </button>
              ) : (
                <form
                  onSubmit={handleTextSubmit}
                  className="w-full max-w-md bg-white/[0.03] border border-white/10 rounded-2xl p-4 flex flex-col gap-2 mt-2 animate-fadeIn"
                >
                  <textarea
                    rows={3}
                    placeholder="Type or paste your note (e.g. 'Ravi owes me 500 rupees by Friday')..."
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setShowTextInput(false)}
                      className="px-3 py-1 rounded-lg text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={status === "processing"}
                      className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
                    >
                      Process Text
                    </button>
                  </div>
                </form>
              )}
            </div>

            <p className="mt-8 text-xs text-slate-500">
              100% Local · Powered by faster-whisper and Gemma on Ollama
            </p>
          </>
        )}
      </div>
    </div>
  );
}
