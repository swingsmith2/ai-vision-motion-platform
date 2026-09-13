# 平台架构

定位：工业 AI / 机器视觉 / 运动控制软件架构，而不是 MCU 驱动练习。

## 分层

```text
apps/sorter          apps/inspector
        \                /
         \              /
          python/avm
     vision   ai   robotics   protocols   viz
                 |
        create_detector()
     opencv | yolo-onnx | ultralytics
               |
         controller (C++)
     PID  Trajectory  GantrySim
               |
     embedded/stm32  (同一套 PID，Wokwi Nucleo 仿真)
```

## 数据流

### 分拣

```text
Scene Image
  → PartDetector (HSV + shape)
  → pixel_to_world(homography)
  → bin assignment
  → avm-motion (trapezoid + PID)
  → overlay / video
```

### 质检

```text
Synthetic / Dataset Image
  → enhance + blackhat/tophat
  → defect blob features
  → ONNX MLP
  → OK / NG
  → VirtualRejectIO (Modbus coil 预留)
```

## 为什么 C++ 和 Python 并存

- Python：视觉、数据、ONNX、报告，迭代快
- C++：运动控制、实时随动、后续要下沉到 Embedded Linux / MCU
- 两者通过 `avm-motion` 作业文件 + CSV 轨迹对接

后续可以把同一套 PID / 轨迹代码做到 STM32 或 EtherCAT 主站，不必重写上层应用。

## 后续接口

| 现在 | 以后替换为 |
|---|---|
| 合成图像 / 数据集 | 工业相机 / V4L2 / GigE |
| OpenCV + 自训 ONNX MLP | YOLO / Segmentation + TensorRT |
| 虚拟 Reject IO | Modbus / PLC |
| 龙门仿真 / STM32 Wokwi PID | 伺服 / EtherCAT / 运动控制卡 |
| 开环 pick-place | 视觉伺服 |
