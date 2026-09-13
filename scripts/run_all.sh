#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"
cmake -S "$ROOT" -B "$ROOT/build" -G Ninja
cmake --build "$ROOT/build" -j"$(nproc)"
ctest --test-dir "$ROOT/build" --output-on-failure
python "$ROOT/apps/inspector/run.py"
python "$ROOT/apps/sorter/run.py"
echo
echo "Inspector: $ROOT/output/inspector/report.html"
echo "Sorter:    $ROOT/output/sorter/report.html"
echo
echo "Open in Windows browser:"
echo "  bash scripts/open_report.sh sorter"
echo "  bash scripts/open_report.sh inspector"
