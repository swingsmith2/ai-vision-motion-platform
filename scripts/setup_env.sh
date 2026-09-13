#!/usr/bin/env bash
set -euo pipefail

OPT="${HOME}/.local/opt"
BIN="${HOME}/.local/bin"
DL="${TMPDIR:-/tmp}/avm-downloads"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$OPT" "$BIN" "$DL"

need() {
  command -v "$1" >/dev/null 2>&1
}

echo "[1/5] CMake / Ninja / clangd"
if ! need cmake; then
  echo "cmake missing in PATH; expected user install at $BIN/cmake"
fi
if ! need ninja; then
  echo "ninja missing in PATH; expected user install at $BIN/ninja"
fi
if ! need clangd; then
  echo "clangd missing in PATH; expected user install at $BIN/clangd"
fi

echo "[2/5] ARM GNU Toolchain"
if [[ ! -x "$BIN/arm-none-eabi-gcc" ]]; then
  ARCHIVE="$DL/arm-gnu.tar.xz"
  if [[ ! -s "$ARCHIVE" ]]; then
    echo "download ARM toolchain..."
    curl -fL --retry 5 -o "$ARCHIVE" \
      "https://developer.arm.com/-/media/Files/downloads/gnu/14.2.rel1/binrel/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi.tar.xz"
  fi
  mkdir -p "$OPT/arm-gnu-toolchain"
  tar -xJf "$ARCHIVE" -C "$OPT/arm-gnu-toolchain" --strip-components=1
  for t in arm-none-eabi-gcc arm-none-eabi-g++ arm-none-eabi-gdb arm-none-eabi-objcopy arm-none-eabi-size; do
    ln -sfn "$OPT/arm-gnu-toolchain/bin/$t" "$BIN/$t"
  done
fi

echo "[3/5] Python venv"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  python3 -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/pip" install -U pip wheel
"$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"

echo "[4/5] Build C++ controller"
# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"
cmake -S "$ROOT" -B "$ROOT/build" -G Ninja
cmake --build "$ROOT/build" -j"$(nproc)"
ctest --test-dir "$ROOT/build" --output-on-failure

echo "[5/5] Done"
echo "Next:"
echo "  source $ROOT/scripts/env.sh"
echo "  python apps/inspector/run.py"
echo "  python apps/sorter/run.py"
