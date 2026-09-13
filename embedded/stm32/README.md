# STM32 Nucleo-C031 + Wokwi

同一套 PID 的 MCU 侧实现。上层协议：

```text
T x y          目标位置（米）
P kp ki kd     增益
R              回零
S              查询 POS
```

源码：

- `firmware/avm_pid.c` — 与 `controller/src/pid.cpp` 同一结构
- `firmware/avm_app.c` — 二轴对象 + 协议
- `firmware/host_main.c` — 本机仿真（`avm-mcu-sim`）
- `firmware/sketch.ino` — Wokwi / Arduino 包装：UART + PWM + LED

建议第一块真板仍是 Nucleo-F401 / G431 + ST-LINK。Wokwi 先用 C031，因为官方支持这条板。
