# Embedded / STM32

运动控制算法已经从 PC 上的 `avm-motion` 下沉了一份 **可移植 C 固件**。

这不是运动控制卡，也不是 EtherCAT。Wokwi 仿的是 **STM32 Nucleo-C031** 上的 PID + UART + PWM。

```text
视觉 / avm-motion 作业
        ↓  文本协议  T x y
 STM32 固件 (同一套 PID / 二轴对象)
        ↓  PWM
   舵机 X / Y（Wokwi 仿真）
```

先跑第 1 步。第 2 步只是为了看板子，不是算法必需。

## 1. 本机仿真（推荐先做）

不需要开发板，不需要 Wokwi 插件。

```bash
source scripts/env.sh
cmake -S . -B build -G Ninja
cmake --build build -j$(nproc)
ctest --test-dir build --output-on-failure -R mcu
./build/embedded/stm32/avm-mcu-sim --target 0.12,0.08
```

预期：`err` 小于 `0.008`（8 mm）。本次本机结果大约 0.6 mm。

当串口用：

```bash
./build/embedded/stm32/avm-mcu-sim --repl
T 0.18 0.04
S
```

| 命令 | 作用 |
|---|---|
| `T x y` | 目标（米） |
| `P kp ki kd` | PID 增益 |
| `R` | 回零 |
| `S` | 查询 `POS` |

## 2. Wokwi 图形仿真

### 要不要装插件？

| 你想做什么 | 要不要 Wokwi |
|---|---|
| 验证 PID、给简历写「固件已下沉」 | 不用。跑 `avm-mcu-sim` |
| 看 Nucleo、舵机转、串口监视器 | 要。装 Wokwi 扩展 |

### 安装

1. Cursor 左侧扩展 → 搜 `Wokwi` → 安装 **Wokwi Simulator**
2. `F1` → `Wokwi: Request a new License`
3. 浏览器打开后点 **GET YOUR LICENSE**，登录（没有账号就注册，免费）
4. 允许把许可证发回 Cursor，直到提示 License activated

### 启动

1. 在资源管理器里打开 `embedded/stm32/firmware/`（这里有 `diagram.json`）
2. `F1` → `Wokwi: Start Simulator`
3. 串口在 **Wokwi 窗口下半部分**，不在 Cursor 底部的「终端 / 输出」里

接线：USART2（PA2/PA3）→ 串口监视器，PA6/PA7 → 两路舵机，PA5 → 到位 LED。

### 找不到 Serial Monitor？

Cursor 没有单独的「Serial Monitor」面板。它在 **Wokwi Simulator 标签页底部**。

默认是有串口输出才弹出。`diagram.json` 已设 `"display": "always"`，停掉仿真再 `F1` → `Wokwi: Start Simulator`，窗口下面应出现输入框。

当前加载的是 `avm-idle.hex`，**不会打印任何字**，输入 `T ...` 也没反应。要打字交互请用：

```bash
./build/embedded/stm32/avm-mcu-sim --repl
```

可选：装 VS Code/Cursor 扩展 **Serial Monitor**，连接 `rfc2217://localhost:4000`（见 `wokwi.toml`）。仿真标签要保持可见，否则 Wokwi 会暂停。

### 内存

Wokwi 插件**没有官方内存上限**。把 `sketch.ino` 当成 firmware 加载时，仿真器会把文本当机器码执行，内存可以涨到几十 GB。

仓库现在加载 `avm-stm32.hex`（上电自动跟到 `0.20, 0.10`）。看完立刻停止。内存不掉就重启 Cursor。

### 若看不到舵机动作

1. 先停掉仿真，再 `F1` → `Wokwi: Start Simulator`，或点绿色播放
2. 舵机应转到不同角度，绿灯亮
3. 终端里的 `avm-mcu-sim` **不会**驱动这块板。要在 Wokwi 窗口底部串口输入 `T 0.05 0.30`

可以这样：

1. 继续用 `avm-mcu-sim`（算法已经测过）
2. 打开 [Wokwi 新建 Nucleo-C031](https://wokwi.com/projects/new/st-nucleo-c031c6)，把 `firmware/sketch.ino`、`avm_pid.c`、`avm_app.c` 以及对应头文件贴进去，网页端会编译
3. 以后用 Cube / `arm-none-eabi-gcc` 编出真正的 `.elf`，再改 `firmware/wokwi.toml`

## 明确不是什么

| 有 | 没有 |
|---|---|
| STM32 风格 PID 固件 | 运动控制卡 / 脉冲卡 |
| 本机 `avm-mcu-sim` | 真伺服 / EtherCAT |
| Wokwi Nucleo 原理图 | 开箱即用的 `.elf` |
