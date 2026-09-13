#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CC="${HOME}/.local/bin/arm-none-eabi-gcc"
OBJCOPY="${HOME}/.local/bin/arm-none-eabi-objcopy"
SIZE="${HOME}/.local/bin/arm-none-eabi-size"
"${CC}" -mcpu=cortex-m0plus -mthumb -ffreestanding -O2 -nostartfiles \
  -T "${DIR}/stm32c031.ld" --specs=nano.specs \
  -o "${DIR}/avm-stm32.elf" \
  "${DIR}/mcu_main.c" "${DIR}/avm_pid.c" "${DIR}/avm_app.c" -lm
"${OBJCOPY}" -O ihex "${DIR}/avm-stm32.elf" "${DIR}/avm-stm32.hex"
"${SIZE}" "${DIR}/avm-stm32.elf"
echo wrote "${DIR}/avm-stm32.elf"
