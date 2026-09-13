#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "apps"))

from avm.ai.detector import ImageDefectDetector
from avm.ai.image_features import extract_image_features
from avm.ai.onnx_mlp import OnnxMLP, OnnxRuntimeClassifier
from avm.data.neu_cls import NEU_LABELS, load_neu_cls, split_dataset
from avm.protocols.reject_io import VirtualRejectIO
from avm.report import card, write_html


def annotate(image: np.ndarray, result, gt: str) -> np.ndarray:
    vis = image.copy()
    if vis.ndim == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
    color = (80, 200, 120) if result.label == gt else (60, 60, 230)
    if result.bbox:
        x, y, w, h = result.bbox
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
    text = f"gt={gt} pred={result.label} {result.confidence:.2f}"
    cv2.putText(vis, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    return vis


def confusion_and_metrics(y_true: list[str], y_pred: list[str], labels: tuple[str, ...]) -> dict:
    matrix = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        if t in matrix and p in matrix[t]:
            matrix[t][p] += 1
    acc = sum(t == p for t, p in zip(y_true, y_pred)) / max(len(y_true), 1)
    per_class = {}
    for label in labels:
        support = sum(t == label for t in y_true)
        correct = sum(t == p == label for t, p in zip(y_true, y_pred))
        per_class[label] = correct / support if support else 0.0
    return {
        "accuracy": acc,
        "per_class_recall": per_class,
        "confusion": matrix,
        "support": dict(Counter(y_true)),
    }


def features_of(samples) -> tuple[np.ndarray, np.ndarray]:
    xs = []
    ys = []
    index = {n: i for i, n in enumerate(NEU_LABELS)}
    for s in samples:
        image = cv2.imread(str(s.path), cv2.IMREAD_COLOR)
        if image is None:
            image = cv2.imread(str(s.path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        xs.append(extract_image_features(image))
        ys.append(index[s.label])
    return np.stack(xs), np.array(ys, dtype=np.int64)


def main() -> int:
    parser = argparse.ArgumentParser(description="Industrial visual inspection on NEU-CLS")
    parser.add_argument("--config", default=str(ROOT / "configs" / "inspector.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output" / "inspector"))
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    vis_dir = out / "annotated"
    model_dir = out / "model"
    out.mkdir(parents=True, exist_ok=True)
    if vis_dir.exists():
        for old in vis_dir.glob("*"):
            old.unlink()
    vis_dir.mkdir(parents=True, exist_ok=True)

    dataset_root = Path(cfg["dataset_root"]) if cfg.get("dataset_root") else None
    if dataset_root and not dataset_root.is_absolute():
        dataset_root = ROOT / dataset_root
    samples = load_neu_cls(dataset_root)
    train, val = split_dataset(samples, val_ratio=cfg.get("val_ratio", 0.2), seed=cfg.get("split_seed", 7))
    x_train, y_train = features_of(train)
    mlp = OnnxMLP.train(
        x_train,
        y_train,
        NEU_LABELS,
        hidden=cfg.get("hidden", 32),
        lr=cfg.get("lr", 0.08),
        epochs=cfg.get("epochs", 500),
    )
    onnx_path = mlp.export_onnx(model_dir / "neu_cls_mlp.onnx")
    native_acc = float((mlp.predict(x_train) == y_train).mean())

    clf = OnnxRuntimeClassifier(onnx_path, NEU_LABELS)
    detector = ImageDefectDetector(clf)
    io = VirtualRejectIO(out / "reject_io.json", coil=cfg.get("reject_coil", "Q0.1"))

    y_true: list[str] = []
    y_pred: list[str] = []
    records = []
    latencies = []
    preview = {label: 0 for label in NEU_LABELS}
    cards = []

    for i, sample in enumerate(val):
        image = cv2.imread(str(sample.path), cv2.IMREAD_COLOR)
        if image is None:
            image = cv2.imread(str(sample.path), cv2.IMREAD_GRAYSCALE)
        t0 = time.perf_counter()
        result = detector.infer(image)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        y_true.append(sample.label)
        y_pred.append(result.label)
        io.emit(f"{i:04d}", result.ok, result.label, result.confidence, result.reason)
        records.append(
            {
                "file": sample.path.name,
                "label": sample.label,
                "pred": result.label,
                "confidence": result.confidence,
                "ok": result.ok,
            }
        )
        if preview[sample.label] < cfg.get("preview_per_class", 3):
            vis_name = f"{sample.label}_{preview[sample.label]:02d}_{sample.path.stem}.png"
            cv2.imwrite(str(vis_dir / vis_name), annotate(image, result, sample.label))
            cards.append(
                card(
                    f"annotated/{vis_name}",
                    f"gt={sample.label} pred={result.label} {result.confidence:.2f}",
                )
            )
            preview[sample.label] += 1

    metrics = confusion_and_metrics(y_true, y_pred, NEU_LABELS)
    metrics["train_acc"] = native_acc
    metrics["avg_latency_ms"] = float(np.mean(latencies))
    metrics["p95_latency_ms"] = float(np.percentile(latencies, 95))
    metrics["dataset"] = "NEU-CLS"
    metrics["train_size"] = len(train)
    metrics["val_size"] = len(val)
    metrics["onnx_model"] = "model/neu_cls_mlp.onnx"
    io.dump()
    (out / "metrics.json").write_text(json.dumps({"metrics": metrics, "records": records}, indent=2), encoding="utf-8")

    summary = (
        f"公开数据集 <code>NEU-CLS</code>（东北大学热轧带钢表面缺陷，1800 张 / 6 类）上的边缘质检。"
        f" 训练 {len(train)} 张，评测 {len(val)} 张。"
        f" ONNX Runtime CPU 准确率 {metrics['accuracy']:.1%}，平均延迟 {metrics['avg_latency_ms']:.2f} ms。"
        f" 全部缺陷样本按 NG 写入虚拟剔除线圈 <code>{cfg.get('reject_coil', 'Q0.1')}</code>。"
    )
    write_html(
        out / "report.html",
        "工业视觉缺陷检测 · NEU-CLS",
        summary,
        cards,
        metrics=[
            ("Dataset", "NEU-CLS"),
            ("Accuracy", f"{metrics['accuracy']:.1%}"),
            ("Train acc", f"{native_acc:.1%}"),
            ("Val size", str(len(val))),
            ("Latency", f"{metrics['avg_latency_ms']:.2f} ms"),
            ("Classes", "6"),
        ],
    )
    print(json.dumps({k: metrics[k] for k in metrics if k != "confusion"}, indent=2, ensure_ascii=False))
    print(f"report: {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
