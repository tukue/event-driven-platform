#!/usr/bin/env bash
set -euo pipefail

# Run from the project root directory.
cd "$(dirname "${BASH_SOURCE[0]}")"

PROJECT_ROOT="$(pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"

info() {
  printf '%s\n' "$1"
}

error() {
  printf 'Error: %s\n' "$1" >&2
}

python_cmd() {
  if command -v python >/dev/null 2>&1; then
    printf '%s\n' python
  elif command -v py >/dev/null 2>&1; then
    printf '%s\n' py
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s\n' python3
  else
    return 1
  fi
}

activate_hint() {
  if [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    printf '  source backend/venv/Scripts/activate\n'
  else
    printf '  source backend/venv/bin/activate\n'
  fi
}

info "Setting up Python virtual environment for Event-Driven Platform..."

PYTHON_BIN="$(python_cmd)" || {
  error "No Python interpreter found. Install Python and retry."
  exit 1
}

info "Using interpreter: $PYTHON_BIN"
info "Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

if [[ -f "$VENV_DIR/Scripts/python.exe" ]]; then
  VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
else
  VENV_PYTHON="$VENV_DIR/bin/python"
fi

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"

info "Python environment setup complete."
info "Activate it with:"
activate_hint
