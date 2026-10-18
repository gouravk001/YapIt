const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getAudioExtension(mimeType) {
  if (!mimeType) return ".wav";
  if (mimeType.includes("webm")) return ".webm";
  if (mimeType.includes("mp4")) return ".mp4";
  if (mimeType.includes("ogg")) return ".ogg";
  return ".wav";
}

export class ApiError extends Error {
  constructor(message, { code = null, transcript = null } = {}) {
    super(message);
    this.code = code;
    this.transcript = transcript;
  }
}

async function send(endpoint, options) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, options);
  } catch {
    throw new ApiError("Can't reach the YapIt backend. Is it running?", { code: "Offline" });
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail || `${response.status} ${response.statusText}`, {
      code: body?.error,
      transcript: body?.transcript,
    });
  }
  return response;
}

async function request(endpoint, options = {}) {
  const response = await send(endpoint, options);
  return response.status === 204 ? null : response.json();
}

// Reads the pipeline's NDJSON stream: {"stage"} lines, then one {"draft"} or {"error"} line.
async function streamDraft(endpoint, options, onStage) {
  const response = await send(endpoint, options);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      const event = JSON.parse(line);
      if (event.stage) onStage(event.stage);
      if (event.draft) return event.draft;
      if (event.error) {
        throw new ApiError(event.detail, { code: event.error, transcript: event.transcript });
      }
    }
    if (done) throw new ApiError("The connection closed before the note was ready.");
  }
}

export async function processAudio(audioBlob, capturedAt, timezone, onStage = () => {}) {
  const ext = getAudioExtension(audioBlob.type);
  const formData = new FormData();
  formData.append("audio", audioBlob, `recording${ext}`);
  formData.append("captured_at", capturedAt);
  formData.append("timezone", timezone);

  return streamDraft("/notes/process/stream", { method: "POST", body: formData }, onStage);
}

export async function processText(transcript, capturedAt, timezone, onStage = () => {}) {
  return streamDraft(
    "/notes/process-text/stream",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript, captured_at: capturedAt, timezone }),
    },
    onStage,
  );
}

export async function saveNote(noteEnvelope) {
  return request("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(noteEnvelope),
  });
}

export async function getNotes(filters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== null && value !== undefined && value !== "") {
      params.append(key, value);
    }
  }
  const queryString = params.toString() ? `?${params.toString()}` : "";
  return request(`/notes${queryString}`);
}

export async function updateNote(noteId, updates) {
  return request(`/notes/${noteId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}

export async function deleteNote(noteId) {
  return request(`/notes/${noteId}`, {
    method: "DELETE",
  });
}

export async function retypeNote(transcript, typeName, capturedAt, timezone) {
  return request("/notes/retype", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      transcript,
      type_name: typeName,
      captured_at: capturedAt,
      timezone,
    }),
  });
}

export async function getTypes() {
  return request("/types");
}

export async function getModels() {
  return request("/models");
}

