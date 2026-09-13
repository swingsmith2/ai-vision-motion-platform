# 项目 1：AI 视觉自动分拣平台

## 场景

俯视工位上有垫圈、螺母、方块三类工件。视觉识别后变换到世界坐标，再由 C++ 运动控制器规划轨迹并随动到对应料槽。

## 第一版范围

已实现：

- 合成工位图像
- 统一检测接口：`opencv` / `yolo-onnx` / `ultralytics`
- 官方 YOLOv8n 权重 + 分拣三类微调
- 自训 Tiny-YOLO 网格检测器并导出 ONNX
- OpenCV 颜色+形状兜底
- 相机平面单应性（像素 → 米）
- 多路点梯形速度规划
- PID 二轴龙门仿真
- TCP 轨迹 overlay、关键帧、视频、报告

明确不做：

- 真机六轴
- EtherCAT
- 视觉伺服闭环

## 简历写法

Designed an edge AI vision-to-motion pipeline starting from official YOLOv8n weights, fine-tuned on washer/nut/block, then integrating camera-plane homography, trapezoidal trajectory planning and PID gantry control. Built a multi-backend detector interface (Ultralytics / ONNX / OpenCV) with a C++ motion engine.
