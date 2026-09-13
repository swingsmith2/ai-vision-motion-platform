from __future__ import annotations

from pathlib import Path

from avm.ai.base import ObjectDetector
from avm.ai.detector import OpenCvPartDetector


def create_detector(cfg: dict, model_path: Path | None = None, class_model_path: Path | None = None) -> ObjectDetector:
    det_cfg = cfg.get("detector", {})
    backend = det_cfg.get("backend", "opencv")
    names = tuple(det_cfg.get("names") or list(cfg.get("classes", {}).keys()))
    roi_top = int(det_cfg.get("roi_top", 120))
    colors = {name: spec.get("draw_bgr", [200, 200, 200]) for name, spec in cfg.get("classes", {}).items()}

    if backend == "opencv":
        return OpenCvPartDetector(cfg["classes"], roi_top=roi_top)
    if backend == "yolo":
        from avm.ai.yolo import TinyYoloDetector

        if model_path is None:
            raise FileNotFoundError("YOLO backend needs a trained ONNX model")
        return TinyYoloDetector(
            model_path,
            names=names,
            obj_thr=float(det_cfg.get("obj_thr", 0.45)),
            roi_top=roi_top,
            colors=colors,
            class_model_path=class_model_path,
        )
    if backend == "ultralytics":
        from avm.ai.yolo import UltralyticsYoloDetector

        return UltralyticsYoloDetector(
            str(model_path or det_cfg.get("ultralytics_model", "yolov8n.pt")),
            names=names,
            conf=float(det_cfg.get("obj_thr", 0.25)),
            roi_top=roi_top,
            colors=colors,
        )
    raise ValueError(f"unknown detector backend: {backend}")
