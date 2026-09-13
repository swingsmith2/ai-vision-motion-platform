# Embedded 预留

现在的运动控制在 PC 上的 `avm-motion` 里运行。

下一步（有 STM32 开发板之后）：

1. STM32CubeMX 生成 CMake 工程
2. 把 `controller/` 里的 PID / 轨迹算法迁到 MCU
3. UART 上报状态，CAN 发送伺服指令
4. Wokwi 先仿真，再 ST-LINK 烧录

当前不要把时间花在寄存器手册上。
