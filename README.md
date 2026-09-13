# AI Vision & Motion Control Platform

工业边缘视觉 + 运动控制平台。一个仓库，两个作品：

1. **AI 视觉自动分拣**（主项目）
2. **工业视觉缺陷检测 / Edge 部署**（副项目，NEU-CLS 公开数据集）

没有开发板、工业相机、伺服时，也能跑通仿真闭环。检测后端可切换：`opencv` / `yolo-onnx` / `ultralytics`（官方 YOLOv8n + 分拣三类微调）。

当前是 **PC 仿真 + 公开/合成数据 + 虚拟 IO**，不是产线真机。STM32 / ROS2 / EtherCAT 是后续接口，仓库里还没有实现。

## 架构

```text
Camera / Dataset
      ↓
 Vision Engine (OpenCV)
      ↓
 AI Inference (ONNX Runtime)
      ↓
 Coordinate Transform
      ↓
 Motion Planner + PID  (C++)
      ↓
 Gantry Simulator / 后续 Servo
      ↓
 Reject IO / Bin
```

## 依赖

- CMake 3.20+、Ninja、g++
- Python 3.12+
- 可选：`unrar`、`gdown`（重新下载 NEU-CLS 时需要）

本机 WSL 工具链见 [docs/environment.md](docs/environment.md)。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source scripts/env.sh
bash scripts/run_all.sh
```

也可以分步跑：

```bash
cmake -S . -B build -G Ninja
cmake --build build -j$(nproc)
ctest --test-dir build --output-on-failure
python apps/inspector/run.py
python apps/sorter/run.py
```

### 首次复现

| 步骤 | 说明 |
|---|---|
| 质检数据 | 需要 `data/NEU-CLS/`。没有就按 [data/README.md](data/README.md) 下载（约 1800 张） |
| 分拣权重 | 已有 `output/sorter/yolov8/sorter/weights/best.pt` 则跳过微调；否则会生成合成集并训练 YOLOv8n |
| 质检模型 | 每次运行会重训 MLP 并导出 ONNX，通常一两分钟 |
| 完整分拣 | 默认 `ultralytics`。首次无缓存时可能超过 10 分钟；只想快速看链路可用 `opencv` 后端 |

产物：

- `output/sorter/report.html`
- `output/inspector/report.html`

报告是单文件 HTML（图片和中文字体已内嵌），用浏览器打开即可。不要在编辑器里当源码预览。WSL 下可用：

```bash
bash scripts/open_report.sh sorter
bash scripts/open_report.sh inspector
```

## 运行结果

### 分拣报告

YOLOv8 微调识别垫圈 / 螺母 / 方块，单应性变换后由 C++ 梯形规划 + PID 龙门仿真入槽。本次 7 个工件，末端误差约 0.05 mm。

![AI 视觉自动分拣平台报告](docs/images/sorter-preview.png)

### 质检报告

NEU-CLS（1800 张 / 6 类）上训练 MLP，导出 ONNX 后用 ONNX Runtime CPU 推理。本次评测准确率约 83%，平均延迟约 4 ms。

![工业视觉缺陷检测 · NEU-CLS 报告](docs/images/inspector-preview.png)

## 目录

```text
apps/inspector/     缺陷检测应用
apps/sorter/        视觉分拣应用
controller/         C++ PID / 轨迹 / 龙门仿真
python/avm/         视觉、AI、协议、报告
configs/            运行配置
embedded/           STM32 / FreeRTOS 预留
docs/               架构说明
```
