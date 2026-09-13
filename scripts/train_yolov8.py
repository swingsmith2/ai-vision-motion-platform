#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "apps"))

from avm.ai.yolov8_train import (
    download_official_weights,
    export_onnx,
    export_sorter_yolo_dataset,
    finetune_yolov8,
)


def main() -> int:
    data_yaml = export_sorter_yolo_dataset(ROOT / "data" / "sorter-yolo")
    official = download_official_weights(ROOT / "output" / "sorter" / "model")
    best = finetune_yolov8(
        data_yaml,
        official,
        ROOT / "output" / "sorter" / "yolov8",
        epochs=12,
        imgsz=416,
        batch=8,
    )
    onnx = export_onnx(best, ROOT / "output" / "sorter" / "model" / "yolov8n_sorter.onnx")
    print(f"official: {official}")
    print(f"finetuned: {best}")
    print(f"onnx: {onnx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
