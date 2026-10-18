#!/usr/bin/env bash
# Start the YapIt backend and frontend together. Ctrl+C stops both.
#
# Usage: ./dev.sh [--reload]
#   --reload  restart the backend when Python files change (reloads Whisper each time, so slower)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
FRONTEND_PORT=5173
HEALTH_TIMEOUT_SECONDS=90
MIN_NODE_MAJOR=20
NODE_VERSION_FOR_NVM=24
OLLAMA_URL="http://localhost:11434/api/version"

RELOAD_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --reload) RELOAD_FLAG="--reload" ;;
    -h | --help)
      sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

BOLD=$'\e[1m'
DIM=$'\e[2m'
RED=$'\e[31m'
GREEN=$'\e[32m'
YELLOW=$'\e[33m'
BLUE=$'\e[34m'
MAGENTA=$'\e[35m'
RESET=$'\e[0m'

info() { echo "${BOLD}${BLUE}▸${RESET} $*"; }
warn() { echo "${BOLD}${YELLOW}!${RESET} $*"; }
fail() {
  echo "${BOLD}${RED}✗${RESET} $*" >&2
  exit 1
}

env_value() {
  local file="$1" key="$2" default="$3" value
  value="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"'"'"'' || true)"
  echo "${value:-$default}"
}

port_owner() {
  ss -ltnpH "sport = :$1" 2>/dev/null | grep -o 'users:(("[^"]*"' | head -n1 | cut -d'"' -f2
}

require_free_port() {
  local port="$1" name="$2"
  if [[ -n "$(ss -ltnH "sport = :$port" 2>/dev/null)" ]]; then
    local owner
    owner="$(port_owner "$port")"
    fail "Port $port ($name) is already in use${owner:+ by '$owner'}. Stop it first, e.g. ${BOLD}fuser -k $port/tcp${RESET}"
  fi
}

node_major() {
  node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0
}

ensure_node() {
  if [[ "$(node_major)" -ge "$MIN_NODE_MAJOR" ]]; then
    return
  fi
  local nvm_script="${NVM_DIR:-$HOME/.nvm}/nvm.sh"
  [[ -s "$nvm_script" ]] || fail "Node $MIN_NODE_MAJOR+ is required (found $(node -v 2>/dev/null || echo none)). Install it or nvm."
  # nvm reads unset variables, which `set -u` would treat as errors.
  set +u
  # shellcheck source=/dev/null
  source "$nvm_script"
  nvm use "$NODE_VERSION_FOR_NVM" >/dev/null || fail "Run: ${BOLD}nvm install $NODE_VERSION_FOR_NVM${RESET}"
  set -u
}

prefix_output() {
  local label="$1" colour="$2"
  sed -u "s/^/${colour}[${label}]${RESET} /"
}

# --- Preflight -------------------------------------------------------------

[[ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]] ||
  fail "Backend virtualenv not found. See README → Quick start → Backend (python3 -m venv .venv && pip install -r requirements.txt)."
[[ -d "$FRONTEND_DIR/node_modules" ]] ||
  fail "Frontend dependencies missing. Run: ${BOLD}cd frontend && npm install${RESET}"
command -v curl >/dev/null || fail "curl is required."

ensure_node

BACKEND_HOST="$(env_value "$BACKEND_DIR/.env" BACKEND_HOST 127.0.0.1)"
BACKEND_PORT="$(env_value "$BACKEND_DIR/.env" BACKEND_PORT 8000)"
BACKEND_URL="http://localhost:$BACKEND_PORT"

require_free_port "$BACKEND_PORT" backend
require_free_port "$FRONTEND_PORT" frontend

if ! curl -sf -m 2 "$OLLAMA_URL" >/dev/null; then
  warn "Ollama isn't answering at $OLLAMA_URL. Notes can't be processed until it runs: ${BOLD}sudo systemctl start ollama${RESET}"
fi

# --- Start -----------------------------------------------------------------

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  trap - EXIT INT TERM
  echo
  info "Stopping…"
  # Each server runs in its own process group, so this also stops uvicorn workers and vite.
  for pid in "$FRONTEND_PID" "$BACKEND_PID"; do
    [[ -n "$pid" ]] && kill -TERM -- "-$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

info "Starting backend on $BACKEND_URL ${RELOAD_FLAG:+${DIM}(auto-reload)${RESET}}"
cd "$BACKEND_DIR"
# shellcheck disable=SC2086  # RELOAD_FLAG is intentionally empty or a single flag
setsid .venv/bin/uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" $RELOAD_FLAG \
  > >(prefix_output backend "$MAGENTA") 2>&1 &
BACKEND_PID=$!

info "Waiting for the backend to load its models…"
deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
until curl -sf -m 2 "$BACKEND_URL/health" >/dev/null; do
  kill -0 "$BACKEND_PID" 2>/dev/null || fail "Backend exited during startup. See the [backend] lines above."
  ((SECONDS < deadline)) || fail "Backend didn't become healthy within ${HEALTH_TIMEOUT_SECONDS}s."
  sleep 1
done

info "Starting frontend on http://localhost:$FRONTEND_PORT"
cd "$FRONTEND_DIR"
setsid npm run dev -- --port "$FRONTEND_PORT" --strictPort \
  > >(prefix_output frontend "$GREEN") 2>&1 &
FRONTEND_PID=$!

until curl -sf -m 2 "http://localhost:$FRONTEND_PORT" >/dev/null; do
  kill -0 "$FRONTEND_PID" 2>/dev/null || fail "Frontend exited during startup. See the [frontend] lines above."
  sleep 0.5
done

echo
echo "  ${BOLD}${GREEN}YapIt is running${RESET}"
echo "  App       ${BOLD}http://localhost:$FRONTEND_PORT${RESET}"
echo "  API docs  $BACKEND_URL/docs"
echo "  ${DIM}Press Ctrl+C to stop both.${RESET}"
echo

# If either server stops, stop the other and report it.
set +e
wait -n "$BACKEND_PID" "$FRONTEND_PID"
status=$?
set -e
warn "A server stopped (exit $status). Shutting down the other."
exit "$status"
