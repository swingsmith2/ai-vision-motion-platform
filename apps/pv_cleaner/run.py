#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "apps"))

from avm.report import card, write_html
from avm.vision.line_follow import detect_aluminum_line
from avm.viz.pv_cleaner import draw_camera, draw_pipeline, draw_world
from pv_cleaner.generate_scene import camera_view, render_pv_array


def nearest_seam(seam_xs: list[int], x: float) -> float:
    return float(min(seam_xs, key=lambda s: abs(s - x)))


def main() -> int:
    parser = argparse.ArgumentParser(description="PV aluminum-frame line following sim")
    parser.add_argument("--config", default=str(ROOT / "configs" / "pv_cleaner.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output" / "pv_cleaner"))
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)

    world = render_pv_array(
        width=int(cfg["image"]["width"]),
        height=int(cfg["image"]["height"]),
        panel_w=int(cfg["panel"]["width_px"]),
        panel_h=int(cfg["panel"]["height_px"]),
        frame=int(cfg["panel"]["frame_px"]),
        mm_per_px=float(cfg["panel"]["mm_per_px"]),
        seed=int(cfg.get("seed", 3)),
    )
    mm = world.mm_per_px
    cam_w, cam_h = int(cfg["camera"]["width"]), int(cfg["camera"]["height"])
    dt = float(cfg["robot"]["dt"])
    speed = float(cfg["robot"]["speed_px_s"])
    steps = int(cfg["robot"]["steps"])
    max_rate = float(cfg["robot"]["max_yaw_rate"])
    pid = cfg["pid"]

    seam = nearest_seam(world.seam_xs, world.image.shape[1] * 0.42)
    x = seam + float(cfg["robot"]["start_offset_px"])
    y = 140.0
    theta = np.deg2rad(float(cfg["robot"]["start_yaw_deg"]))

    cv2.imwrite(str(out / "world.png"), world.image)
    cv2.imwrite(str(out / "pipeline.png"), draw_pipeline())

    path: list[tuple[float, float]] = [(x, y)]
    lat_mm: list[float] = []
    vis_mm: list[float] = []
    detect_ms: list[float] = []
    lost_n = 0
    prev_x: float | None = None
    prev_ey = 0.0
    lost_run = 0
    first_cam = None
    last_cam = None
    key_idxs = {0, steps // 4, steps // 2, (3 * steps) // 4, steps - 1}

    video_path = out / "follow.mp4"
    writer = None

    for i in range(steps):
        view = camera_view(world.image, x, y, theta, cam_w, cam_h)
        t0 = time.perf_counter()
        obs = detect_aluminum_line(view, prev_x=prev_x)
        detect_ms.append((time.perf_counter() - t0) * 1000.0)
        lost = not obs.found
        if lost:
            lost_n += 1
            lost_run += 1
            ey, eth = prev_ey * 0.6, 0.0
            if lost_run >= 4:
                prev_x = None
        else:
            lost_run = 0
            prev_x = obs.x_near
            ey, eth = obs.e_y_px, obs.e_theta_rad
        dey = ey - prev_ey
        prev_ey = ey
        # e_theta sign: positive camera tilt means heading is already to the right of the seam.
        steer = float(pid["kp_y"]) * ey + float(pid["kd_y"]) * dey - float(pid["kp_theta"]) * eth
        steer = float(np.clip(steer, -float(pid["max_steer"]), float(pid["max_steer"])))
        omega = float(np.clip(steer, -max_rate, max_rate))
        theta = float(np.clip(theta + omega * dt, -0.6, 0.6))
        x += speed * np.sin(theta) * dt
        y += speed * np.cos(theta) * dt
        y = float(np.clip(y, 40, world.image.shape[0] - 80))
        x = float(np.clip(x, 40, world.image.shape[1] - 40))
        path.append((x, y))

        true_mm = (x - seam) * mm
        cam_mm = ey * mm
        lat_mm.append(true_mm)
        vis_mm.append(cam_mm)

        cam = draw_camera(view, obs, e_y_mm=cam_mm, e_theta_deg=np.degrees(eth), step=i, lost=lost)
        if first_cam is None:
            first_cam = cam
            cv2.imwrite(str(out / "camera_start.png"), cam)
        last_cam = cam
        if i in key_idxs:
            overview = draw_world(world.image, path, x, y, theta, seam)
            cv2.imwrite(str(frames_dir / f"world_{i:03d}.png"), overview)
            cv2.imwrite(str(frames_dir / f"cam_{i:03d}.png"), cam)

        if writer is None:
            oh, ow = cam.shape[:2]
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 20, (ow, oh))
        if writer is not None and writer.isOpened() and i % 2 == 0:
            writer.write(cam)

    if writer is not None:
        writer.release()
    cv2.imwrite(str(out / "camera_end.png"), last_cam)
    overview = draw_world(world.image, path, x, y, theta, seam)
    cv2.imwrite(str(out / "overlay.png"), overview)

    lat = np.array(lat_mm)
    vis = np.array(vis_mm)
    rms = float(np.sqrt(np.mean(lat**2)))
    final = float(abs(lat[-1]))
    peak = float(np.max(np.abs(lat)))
    mean_ms = float(np.mean(detect_ms))
    wrote_video = video_path.exists() and video_path.stat().st_size > 0

    summary = {
        "locked_seam_px": seam,
        "start_offset_mm": float(cfg["robot"]["start_offset_px"]) * mm,
        "steps": steps,
        "true_lateral_rms_mm": round(rms, 2),
        "true_lateral_peak_mm": round(peak, 2),
        "true_lateral_final_mm": round(final, 2),
        "vision_e_y_rms_mm": round(float(np.sqrt(np.mean(vis**2))), 2),
        "lost_frames": lost_n,
        "detect_p50_ms": round(float(np.percentile(detect_ms, 50)), 2),
        "detect_mean_ms": round(mean_ms, 2),
        "video": video_path.name if wrote_video else None,
        "backend": "opencv-hough",
        "note": "synthetic top-down PV array, not a field robot",
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    cards = [
        card("pipeline.png", "相机 → 铝框提取 → 横向/航向偏差 → PID → 差速"),
        card("overlay.png", "世界坐标轨迹贴着锁定的纵缝"),
        card("camera_start.png", "起步：有横向偏移和航向偏差"),
        card("camera_end.png", "结束：相机里铝框回到中轴附近"),
        card("world.png", "合成光伏阵列（铝框为跟线目标）"),
    ]
    for name in sorted(p.name for p in frames_dir.glob("cam_*.png")):
        cards.append(card(f"frames/{name}", f"相机关键帧 {name}"))

    html_summary = (
        "光伏板清扫跟线仿真：合成俯视阵列，用 OpenCV 提取铝框纵缝，"
        "估计横向偏差 <code>e_y</code> 与航向偏差 <code>e_θ</code>，PID 纠偏。"
        f" 起步偏置 {summary['start_offset_mm']:.0f} mm，"
        f"真实横向 RMS {rms:.1f} mm，峰值 {peak:.1f} mm，终点 {final:.1f} mm。"
        f" 丢线 {lost_n}/{steps} 帧，提线平均 {mean_ms:.1f} ms。"
        " 这是合成俯视仿真，不是电站真机。"
    )
    write_html(
        out / "report.html",
        "光伏铝框跟线仿真",
        html_summary,
        cards,
        metrics=[
            ("Backend", "OpenCV"),
            ("RMS", f"{rms:.1f} mm"),
            ("Peak", f"{peak:.1f} mm"),
            ("Final", f"{final:.1f} mm"),
            ("Lost", f"{lost_n}/{steps}"),
            ("Detect", f"{mean_ms:.1f} ms"),
        ],
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"report: {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
