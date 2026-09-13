#!/usr/bin/env bash
# Source this file:  source scripts/env.sh
export PATH="$HOME/.local/bin:$PATH"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AVM_ROOT="$ROOT"
if [[ -d "$ROOT/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi
export PYTHONPATH="$ROOT/python:$ROOT/apps:${PYTHONPATH:-}"
echo "AVM env ready: cmake=$(command -v cmake) ninja=$(command -v ninja) python=$(command -v python)"
