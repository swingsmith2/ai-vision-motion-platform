from __future__ import annotations

import cv2
import numpy as np

from avm.vision.line_follow import LineObservation


def _put(img, text, org, color=(236, 240, 245), scale=0.5, thick=1):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (12, 12, 12), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def draw_pipeline(width: int = 800, height: int = 150) -> np.ndarray:
    img = np.full((height, width, 3), 22, dtype=np.uint8)
    stages = [
        ("Camera", (90, 80, 40)),
        ("Al-frame", (50, 160, 190)),
        ("e_y e_th", (40, 160, 120)),
        ("PID", (180, 120, 40)),
        ("Drive", (40, 90, 210)),
    ]
    box_w, gap = 118, 28
    x0 = 36
    cv2.putText(
        img, "PV cleaner: follow aluminum frame", (28, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 220, 230), 1, cv2.LINE_AA,
    )
    for i, (name, color) in enumerate(stages):
        x = x0 + i * (box_w + gap)
        cv2.rectangle(img, (x, 52), (x + box_w, 114), color, 2)
        tw = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]
        cv2.putText(img, name, (x + (box_w - tw) // 2, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)
        if i < len(stages) - 1:
            cv2.arrowedLine(img, (x + box_w + 4, 83), (x + box_w + gap - 6, 83), (180, 190, 200), 2, cv2.LINE_AA, tipLength=0.35)
    return img


def draw_camera(
    view: np.ndarray,
    obs: LineObservation,
    *,
    e_y_mm: float,
    e_theta_deg: float,
    step: int,
    lost: bool,
) -> np.ndarray:
    vis = view.copy()
    h, w = vis.shape[:2]
    cv2.line(vis, (w // 2, 0), (w // 2, h), (80, 90, 100), 1, cv2.LINE_AA)
    if obs.found:
        cv2.line(vis, (obs.x1, obs.y1), (obs.x2, obs.y2), (60, 220, 140), 3, cv2.LINE_AA)
        cv2.circle(vis, (int(round(obs.x_near)), int(h * 0.82)), 6, (40, 80, 255), -1)
    bar = np.full((36, w, 3), 16, dtype=np.uint8)
    vis = np.vstack([bar, vis])
    status = f"CAM  step={step}  e_y={e_y_mm:+.1f}mm  e_th={e_theta_deg:+.1f}deg"
    if lost:
        status += "  LOST"
    color = (80, 80, 230) if lost else (230, 236, 242)
    cv2.putText(vis, status, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)
    return vis


def draw_world(
    world: np.ndarray,
    path: list[tuple[float, float]],
    x: float,
    y: float,
    theta: float,
    seam_x: float,
) -> np.ndarray:
    vis = world.copy()
    h, w = vis.shape[:2]
    cv2.line(vis, (int(seam_x), 0), (int(seam_x), h), (40, 210, 255), 2, cv2.LINE_AA)
    if len(path) > 1:
        pts = np.array(path, dtype=np.int32)
        cv2.polylines(vis, [pts], False, (80, 220, 120), 2, cv2.LINE_AA)
    c, s = np.cos(theta), np.sin(theta)
    body = np.array(
        [
            [18, 28],
            [-18, 28],
            [-18, -22],
            [18, -22],
        ],
        dtype=np.float32,
    )
    rot = np.array([[c, s], [-s, c]], dtype=np.float32)
    pts = (body @ rot.T) + np.array([x, y], dtype=np.float32)
    cv2.fillConvexPoly(vis, pts.astype(np.int32), (70, 70, 80))
    cv2.polylines(vis, [pts.astype(np.int32)], True, (230, 230, 235), 2, cv2.LINE_AA)
    nose = (int(x + 34 * s), int(y + 34 * c))
    cv2.arrowedLine(vis, (int(x), int(y)), nose, (60, 90, 255), 2, cv2.LINE_AA, tipLength=0.35)
    bar = np.full((36, w, 3), 16, dtype=np.uint8)
    vis = np.vstack([bar, vis])
    _put(vis, f"WORLD  seam_x={seam_x:.0f}px  pose=({x:.0f},{y:.0f})  yaw={np.degrees(theta):+.1f}deg", (12, 24), (230, 236, 242), 0.48, 1)
    return vis
