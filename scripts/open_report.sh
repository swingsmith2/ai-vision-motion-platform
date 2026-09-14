#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-sorter}"
FILE="$ROOT/output/$NAME/report.html"
if [[ ! -f "$FILE" ]]; then
  echo "missing: $FILE" >&2
  exit 1
fi

WIN="$(wslpath -w "$FILE" 2>/dev/null || true)"
echo "report: $FILE"
if [[ -n "${WIN}" ]]; then
  echo "windows: $WIN"
fi

open_ok=0
try_open() {
  local bin="$1"
  shift
  if ! command -v "$bin" >/dev/null 2>&1; then
    return 1
  fi
  if "$bin" "$@" >/dev/null 2>&1; then
    open_ok=1
    return 0
  fi
  return 1
}

try_open wslview "$FILE" || true
if [[ "$open_ok" -eq 0 ]]; then
  try_open xdg-open "$FILE" || true
fi
if [[ "$open_ok" -eq 0 && -n "${WIN}" ]]; then
  # Windows interop is optional. explorer.exe often exists in PATH but cannot run.
  if command -v cmd.exe >/dev/null 2>&1; then
    if cmd.exe /c start "" "$WIN" >/dev/null 2>&1; then
      open_ok=1
    fi
  fi
fi

if [[ "$open_ok" -eq 0 ]]; then
  echo "could not launch a browser from this shell (WSL interop / explorer.exe)."
  echo "open the HTML in Windows or Cursor browser, do not preview it as source:"
  echo "  $FILE"
  [[ -n "${WIN}" ]] && echo "  $WIN"
  exit 0
fi
