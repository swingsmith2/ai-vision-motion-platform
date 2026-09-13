# 项目 2：工业视觉缺陷检测

## 场景

热轧带钢表面缺陷检测，数据来自公开数据集 **NEU-CLS**。

类别：`crazing` / `inclusion` / `patches` / `pitted_surface` / `rolled_in_scale` / `scratches`。

## 第一版范围

已实现：

- 接入 NEU-CLS（1800 张 / 6 类）
- 纹理 + 形态学特征（直方图 / LBP / 边缘 / 缺陷密度）
- 自训 MLP 并导出 ONNX
- ONNX Runtime CPU 推理
- 分层划分、混淆矩阵、逐类召回
- 虚拟剔除线圈日志

明确不做：

- 从零训练 SOTA 分割大模型
- TensorRT 工控机部署
- 真实产线相机

## 简历写法

Built an industrial defect-inspection pipeline on the public NEU-CLS steel-surface dataset (1,800 images, 6 defect types). Extracted texture/morphology features, trained an MLP, exported it to ONNX, and deployed inference with ONNX Runtime. Reported accuracy, per-class recall and latency, and mapped NG decisions to a virtual reject coil.
