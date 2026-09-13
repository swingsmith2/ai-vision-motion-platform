# 开发环境

本机是 Ubuntu 24.04 WSL2，没有免密 sudo，因此第一阶段工具装在用户空间。克隆仓库的人不需要照抄这些路径，按仓库根目录 README 的「快速开始」即可。

## 已就绪

- gcc / g++ 13.3
- CMake 3.31.6 → `~/.local/bin/cmake`
- Ninja 1.12.1 → `~/.local/bin/ninja`
- clangd 19.1.2 → `~/.local/bin/clangd`
- ARM GNU Toolchain 14.2.Rel1 → `~/.local/bin/arm-none-eabi-gcc`
- Python 3.12 venv：numpy / opencv-headless / onnx / onnxruntime / pyyaml
- Git
- Cursor 扩展：clangd、CMake Tools、Wokwi、Cortex-Debug

## 建议稍后安装

- STM32CubeMX
- STM32CubeCLT / STM32CubeProgrammer
- Cortex-Debug / OpenOCD（买板后）
- ROS 2 / Gazebo / MoveIt（第 4 阶段）
- TensorRT / OpenVINO（有 GPU/工控机后）

## Cursor 扩展（手动）

在 Cursor 扩展市场安装：

- clangd
- CMake Tools
- Wokwi Embedded Simulator
- Cortex-Debug

STM32 官方 VS Code 扩展如果和 Cursor 不兼容，保留一份 VS Code 备用即可。

## WSL 打开报告

报告在 `output/*/report.html`。Windows 浏览器不要用 `/home/ubuntu/...`，用 UNC 路径或脚本：

```bash
bash scripts/open_report.sh sorter
bash scripts/open_report.sh inspector
```

本机示例：

`\\wsl.localhost\Ubuntu-24.04\home\ubuntu\WorkSpace\Embedded\ai-vision-motion-platform\output\sorter\report.html`
