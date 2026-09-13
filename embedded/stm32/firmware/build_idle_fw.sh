#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CC="${ARM_GCC:-$HOME/.local/bin/arm-none-eabi-gcc}"
OBJCOPY="${CC%-gcc}-objcopy"
"$CC" -mcpu=cortex-m0plus -mthumb -nostdlib -ffreestanding \
  -T "$DIR/stm32c031.ld" -o "$DIR/avm-idle.elf" "$DIR/idle.c"
"$OBJCOPY" -O ihex "$DIR/avm-idle.elf" "$DIR/avm-idle.hex"
echo "wrote $DIR/avm-idle.elf $DIR/avm-idle.hex"
