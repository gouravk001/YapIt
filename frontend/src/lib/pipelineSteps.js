// Stage names streamed by the backend while it turns a recording into a draft.
export const STEP_LABELS = {
  transcribe: "Transcribing",
  classify: "Understanding",
  extract: "Filling in details",
  refine: "Tidying up",
  check: "Double-checking",
};

export const AUDIO_STEPS = ["transcribe", "classify", "extract", "refine", "check"];
export const TEXT_STEPS = AUDIO_STEPS.slice(1);
