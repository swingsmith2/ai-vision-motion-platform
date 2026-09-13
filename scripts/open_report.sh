#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-sorter}"
FILE="$ROOT/output/$NAME/report.html"
if [[ ! -f "$FILE" ]]; then
  echo "missing: $FILE" >&2
  exit 1
fi
WIN="$(wslpath -w "$FILE")"
echo "Opening $WIN"
if command -v wslview >/dev/null 2>&1; then
  wslview "$FILE"
elif command -v explorer.exe >/dev/null 2>&1; then
  explorer.exe "$WIN"
else
  echo "Open this file in a browser:"
  echo "  $FILE"
  echo "  $WIN"
fi
