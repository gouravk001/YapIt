# YapIt

A fully local voice-notes app. Speak a note, and YapIt transcribes it, classifies it (payment, promise, event, info, or general), extracts structured fields, lets you review and correct the draft, then saves it. Everything runs on your machine — no cloud APIs, no data leaving the device.

**Stack:** Python 3.12 · FastAPI · faster-whisper · Gemma 3 4B via Ollama · SQLite · React 19 · Vite · Tailwind CSS 4

---

## Requirements

| Requirement | Minimum |
|---|---|
| OS | Ubuntu 22.04 or 24.04 |
| GPU | NVIDIA with ≥ 8 GB VRAM (RTX 4060 tested) |
| Python | 3.10+ |
| Node.js | 20+ (nvm recommended) |
| Disk | ~5 GB (models) |

---

## Quick start (fresh clone)

### 1. System dependencies

```bash
# NVIDIA driver (if not already installed)
ubuntu-drivers install

# ffmpeg
sudo apt install ffmpeg

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
# Verify:
ollama --version
```

### 2. Pull the Gemma model

```bash
ollama pull gemma3:4b
# Check it works:
ollama run gemma3:4b "Say hello."
```

### 3. Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# Verify the environment (Milestone 1 check)
python scripts/verify_env.py

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs are at http://localhost:8000/docs

### 4. Frontend

```bash
cd frontend

# Node 20+ required (using nvm):
nvm use 24

npm install
npm run dev
```

Open http://localhost:5173

---

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## Running the eval harness

```bash
cd backend
source .venv/bin/activate

# Run eval on the default (configured) models
python -m eval.runner

# Run eval with a specific registry model override
python -m eval.runner --llm gemma3-4b-q4

# Compare saved runs
python -m eval.runner --compare
```

Results are saved to `eval/results/` as JSON files named `<model-id>_<date>.json`.

---

## Swapping a model

Edit `config/models.yaml` only:

1. Add a new entry to the `models` list with a unique `id`, the correct `role`, `runtime`, and `model_name`.
2. Change the matching key under `active` to the new `id`.
3. Restart the backend. No code changes required.

**Example — switching to a different LLM:**

```yaml
models:
  - id: gemma3-4b-q4
    role: llm
    runtime: ollama
    model_name: gemma3:4b
    # ...

  - id: llama3-8b         # new entry
    role: llm
    runtime: ollama
    model_name: llama3:8b
    temperature: 0.1
    top_p: 0.9
    num_ctx: 4096
    vram_mb: 5000

active:
  transcriber: whisper-small-en
  llm: llama3-8b           # <-- changed here only
```

Adding a model that uses a **new runtime** (e.g. llama.cpp) requires one new provider class in `backend/app/providers/`. See `providers/base.py` for the interface.

---

## Fine-tuning readiness (Milestone 8)

To generate training data from the eval dataset in the exact prompt format used at runtime:

```bash
cd backend
source .venv/bin/activate
python scripts/export_training_data.py --output fine_tune/train.jsonl
```

To register a fine-tuned model:
1. Serve it through Ollama: `ollama create my-model -f Modelfile`
2. Add it to `config/models.yaml` with `runtime: ollama` and `model_name: my-model`.
3. Set it as active and restart.

---

## Configuration files

| File | Purpose |
|---|---|
| `backend/config/types.yaml` | Note type definitions (name, fields, examples). Edit to add custom types. |
| `backend/config/models.yaml` | Model registry and active model selection. |
| `backend/.env` | Host, port, DB path, config dir path. |

**Changing a type:** edits to a type's `description` or `examples` apply in place. Adding, removing or changing its `fields` requires bumping its `version`; the backend refuses to start otherwise. Every version is kept in the `note_types` table, so saved notes keep the definition they were created with.

---

## API errors

Every error response has the same shape:

```json
{ "error": "NotFound", "detail": "Note 'abc' not found." }
```

| Status | `error` | When |
|---|---|---|
| 400 | `UnknownType` | Retype with a type name not in `types.yaml` |
| 404 | `NotFound` | Note or route does not exist |
| 422 | `ValidationError` | Request body or form fields are missing or invalid |
| 422 | `TranscriptionFailed` | Uploaded audio could not be decoded |
| 503 | `ModelUnavailable` | Ollama is not running or the model is not pulled |
| 500 | `InternalServerError` | Anything unexpected (details go to the server log, not the client) |

---

## Project layout

```
YapIt/
  frontend/               React + Vite + Tailwind app
    src/
      api/                apiClient.js — all backend calls
      components/         Small, reusable UI components
      hooks/              useRecorder.js, etc.
      pages/              Home.jsx, Notes.jsx
  backend/
    app/
      api/                Thin FastAPI route modules
      services/           Pipeline orchestration, note CRUD
      pipeline/           classify, extract, resolve, validate
      resolvers/          dates, money, people (deterministic)
      providers/          Transcriber + LLM interfaces and implementations
      storage/            SQLite setup and queries
      config/             YAML loaders and pydantic models
    config/               types.yaml, models.yaml
    scripts/              verify_env.py, export_training_data.py
    tests/                Unit tests (deterministic logic only)
    eval/                 Harness, dataset, saved results
```

---

## Final verification (offline)

```bash
# Disable network
sudo nmcli networking off

# Start Ollama (already running as a service after install)
# Start backend and frontend as above

# Re-enable network when done
sudo nmcli networking on
```

Models must already be downloaded. The app works fully offline once models are pulled.

**Audio cleanup:** No audio files are stored. Each recording is written to a temp file, transcribed, and deleted — including on error. Verified by checking `/tmp` before and after a request.

---

## Milestones

- [x] M1: Environment check and setup
- [x] M2: Contracts and configuration  
- [x] M3: Backend structure and model providers
- [x] M4: The pipeline
- [x] M5: Storage and API
- [x] M6: Frontend
- [x] M7: Eval harness
- [x] M8: Fine-tuning readiness

