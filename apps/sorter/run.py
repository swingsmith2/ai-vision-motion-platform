#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "apps"))

from avm.ai.factory import create_detector
from avm.ai.yolo import export_tiny_yolo, train_tiny_yolo
from avm.ai.yolov8_train import (
    download_official_weights,
    export_onnx,
    export_sorter_yolo_dataset,
    finetune_yolov8,
)
from avm.report import card, write_html
from avm.robotics.motion_client import MotionClient
from avm.vision.calibration import CameraCalibration
from avm.vision.geometry import pixel_to_world, world_to_pixel
from avm.viz.sorter import draw_pipeline, draw_sorter_frame
from sorter.generate_scene import make_scene


def find_motion_binary() -> Path:
    candidates = [
        ROOT / "build" / "controller" / "avm-motion",
        ROOT / "build" / "avm-motion",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("avm-motion not found. Build the C++ controller first.")


def _detector_ok(dets, expected: int) -> bool:
    if len(dets) < max(5, expected - 2) or len(dets) > expected + 2:
        return False
    return len({d.name for d in dets}) >= 3


def downsample(points: list[tuple[float, float]], step: int) -> list[tuple[float, float]]:
    if step <= 1:
        return points
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="AI vision sorting cell demo")
    parser.add_argument("--config", default=str(ROOT / "configs" / "sorter.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output" / "sorter"))
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    model_dir = out / "model"
    out.mkdir(parents=True, exist_ok=True)

    width, height = cfg["image"]["width"], cfg["image"]["height"]
    scene, _gt = make_scene(width, height, seed=cfg.get("seed", 5))
    cv2.imwrite(str(out / "scene.png"), scene)
    cv2.imwrite(str(out / "pipeline.png"), draw_pipeline(width, 160))

    names = tuple(cfg.get("detector", {}).get("names") or list(cfg["classes"].keys()))
    det_cfg = cfg.get("detector", {})
    opencv = create_detector({**cfg, "detector": {**det_cfg, "backend": "opencv"}})
    cv_parts = opencv.infer(scene)

    ultra_parts = []
    yolo_parts = []
    official_pt = None
    finetuned_pt = None
    onnx_path = None
    backend = opencv.backend
    parts = cv_parts

    if det_cfg.get("backend") == "ultralytics":
        data_yaml = export_sorter_yolo_dataset(ROOT / "data" / "sorter-yolo", width=width, height=height)
        official_pt = download_official_weights(model_dir, det_cfg.get("ultralytics_model", "yolov8n.pt"))
        finetuned_pt = finetune_yolov8(
            data_yaml,
            official_pt,
            out / "yolov8",
            epochs=int(det_cfg.get("epochs", 12)),
            imgsz=int(det_cfg.get("imgsz", 416)),
            batch=int(det_cfg.get("batch", 8)),
        )
        try:
            onnx_path = export_onnx(finetuned_pt, model_dir / "yolov8n_sorter.onnx")
        except Exception as exc:  # export is optional
            print(f"YOLOv8 ONNX export skipped: {exc}", file=sys.stderr)
        ultra = create_detector({**cfg, "detector": {**det_cfg, "backend": "ultralytics"}}, finetuned_pt)
        ultra_parts = ultra.infer(scene)
        if _detector_ok(ultra_parts, expected=len(cv_parts) or 7):
            parts, backend = ultra_parts, ultra.backend
    else:
        det_mlp, cls_mlp = train_tiny_yolo(
            scene_fn=lambda seed: make_scene(width, height, seed=seed),
            names=names,
            n_scenes=det_cfg.get("train_scenes", 40),
            roi_top=int(det_cfg.get("roi_top", 120)),
        )
        onnx_path = export_tiny_yolo(det_mlp, model_dir / "tiny_yolo.onnx")
        cls_path = cls_mlp.export_onnx(model_dir / "tiny_yolo_cls.onnx")
        yolo = create_detector({**cfg, "detector": {**det_cfg, "backend": "yolo"}}, onnx_path, class_model_path=cls_path)
        yolo_parts = yolo.infer(scene)
        if _detector_ok(yolo_parts, expected=len(cv_parts) or 7):
            parts, backend = yolo_parts, yolo.backend

    if not parts:
        raise RuntimeError("no parts detected")

    calib = CameraCalibration.synthetic_topdown(
        width, height, cfg["table"]["width_m"], cfg["table"]["height_m"]
    )
    bins = {name: tuple(xy) for name, xy in cfg["bins"].items()}
    home = tuple(cfg["home"])
    client = MotionClient(find_motion_binary(), out / "jobs")

    waypoints = [home]
    jobs = []
    pose = home
    for i, part in enumerate(parts):
        wx, wy = pixel_to_world(part.centroid[0], part.centroid[1], calib)
        dest = bins[part.name]
        pick = (wx, wy)
        via = [(pose[0], pose[1]), pick, dest]
        result = client.plan_and_follow(via, job_name=f"pick_{i:02d}_{part.name}")
        jobs.append(
            {
                "part": part.name,
                "backend": part.backend,
                "confidence": round(part.confidence, 3),
                "pixel": [round(part.centroid[0], 1), round(part.centroid[1], 1)],
                "world": [round(wx, 4), round(wy, 4)],
                "bin": list(dest),
                "final_error_m": result.final_error,
                "samples": len(result.samples),
            }
        )
        waypoints.extend([pick, dest])
        pose = dest
    waypoints.append(home)
    full = client.plan_and_follow(waypoints, job_name="full_cycle")

    path_scene = []
    for x, y in downsample(full.path, 8):
        u, v = world_to_pixel(x, y, calib)
        path_scene.append((int(round(u)), int(round(v))))

    overlay = draw_sorter_frame(
        scene, parts, path_scene, path_scene[-1] if path_scene else None,
        backend=backend, error_mm=full.final_error * 1000.0,
        pick_index=len(jobs), total_picks=len(parts),
    )
    cv2.imwrite(str(out / "overlay.png"), overlay)

    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    key_indexes = np.linspace(0, max(len(path_scene) - 1, 0), num=min(8, max(len(path_scene), 1)), dtype=int)
    cards = [
        card("pipeline.png", "视觉 → 决策 → 运动 流水线"),
        card("scene.png", "原始分拣工位"),
        card("overlay.png", f"检测 + 轨迹 overlay（{backend}）"),
    ]
    for k, idx in enumerate(key_indexes):
        name = f"frame_{k:02d}.png"
        cv2.imwrite(
            str(frames_dir / name),
            draw_sorter_frame(
                scene, parts, path_scene[: idx + 1], path_scene[idx],
                backend=backend, error_mm=full.final_error * 1000.0,
                pick_index=len(jobs), total_picks=len(parts),
            ),
        )
        cards.append(card(f"frames/{name}", f"运动关键帧 {k}"))

    video_path = out / "sorting.mp4"
    oh, ow = overlay.shape[:2]
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 20, (ow, oh))
    wrote_video = False
    if writer.isOpened():
        stride = max(1, len(path_scene) // 120)
        for i in range(0, len(path_scene), stride):
            writer.write(
                draw_sorter_frame(
                    scene, parts, path_scene[: i + 1], path_scene[i],
                    backend=backend, error_mm=full.final_error * 1000.0,
                    pick_index=len(jobs), total_picks=len(parts),
                )
            )
        writer.release()
        wrote_video = video_path.exists() and video_path.stat().st_size > 0

    summary = {
        "backend_used": backend,
        "ultralytics_detections": len(ultra_parts),
        "yolo_detections": len(yolo_parts),
        "opencv_detections": len(cv_parts),
        "official_weights": str(official_pt) if official_pt else None,
        "finetuned_weights": str(finetuned_pt) if finetuned_pt else None,
        "onnx_model": str(onnx_path) if onnx_path else None,
        "detected_parts": [
            {
                "name": p.name,
                "pixel": [round(p.centroid[0], 1), round(p.centroid[1], 1)],
                "confidence": round(p.confidence, 3),
                "backend": p.backend,
            }
            for p in parts
        ],
        "jobs": jobs,
        "full_cycle_error_m": full.final_error,
        "full_cycle_samples": len(full.samples),
        "video": str(video_path.name) if wrote_video else None,
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    html_summary = (
        f"统一检测接口已接入 <code>opencv</code> / <code>yolo-onnx</code> / <code>ultralytics</code>。"
        f" 本次使用 <code>{backend}</code>。"
        f" Ultralytics {len(ultra_parts)}，自定义 YOLO {len(yolo_parts)}，OpenCV {len(cv_parts)}。"
        f" 完成识别 → 坐标变换 → 轨迹规划 → PID 随动，末端误差 {full.final_error*1000:.2f} mm。"
    )
    write_html(
        out / "report.html",
        "AI 视觉自动分拣平台",
        html_summary,
        cards,
        metrics=[
            ("Backend", backend),
            ("Parts", str(len(parts))),
            ("YOLOv8", str(len(ultra_parts) or len(yolo_parts))),
            ("OpenCV", str(len(cv_parts))),
            ("Error", f"{full.final_error*1000:.2f} mm"),
            ("Samples", str(len(full.samples))),
        ],
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"report: {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
