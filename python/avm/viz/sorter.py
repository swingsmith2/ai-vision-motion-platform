from __future__ import annotations

import cv2
import numpy as np

from avm.ai.base import Detection


def _put(img, text, org, color=(236, 240, 245), scale=0.5, thick=1):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (12, 12, 12), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def draw_pipeline(width: int = 800, height: int = 160) -> np.ndarray:
    img = np.full((height, width, 3), 22, dtype=np.uint8)
    stages = [
        ("Camera", (90, 80, 40)),
        ("YOLO", (50, 120, 190)),
        ("Coord", (40, 160, 120)),
        ("Plan", (180, 120, 40)),
        ("PID", (40, 90, 210)),
    ]
    box_w, gap = 118, 28
    x0 = 36
    cv2.putText(img, "AVM pipeline: Vision -> Decision -> Motion", (28, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 220, 230), 1, cv2.LINE_AA)
    for i, (name, color) in enumerate(stages):
        x = x0 + i * (box_w + gap)
        cv2.rectangle(img, (x, 52), (x + box_w, 114), color, 2)
        tw = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0][0]
        cv2.putText(img, name, (x + (box_w - tw) // 2, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
        if i < len(stages) - 1:
            cv2.arrowedLine(img, (x + box_w + 4, 83), (x + box_w + gap - 6, 83), (180, 190, 200), 2, cv2.LINE_AA, tipLength=0.35)
    return img


def draw_sorter_frame(
    scene: np.ndarray,
    parts: list[Detection],
    path_px: list[tuple[int, int]],
    current: tuple[int, int] | None,
    *,
    backend: str,
    error_mm: float | None = None,
    pick_index: int | None = None,
    total_picks: int | None = None,
) -> np.ndarray:
    vis = scene.copy()
    h, w = vis.shape[:2]

    if len(path_px) > 1:
        overlay = vis.copy()
        pts = np.array(path_px, dtype=np.int32)
        cv2.polylines(overlay, [pts], False, (110, 220, 150), 3, cv2.LINE_AA)
        vis = cv2.addWeighted(overlay, 0.55, vis, 0.45, 0)
        cv2.polylines(vis, [pts], False, (140, 240, 170), 1, cv2.LINE_AA)

    for i, part in enumerate(parts):
        x, y, bw, bh = part.bbox
        color = part.color_bgr
        cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, 2)
        badge = f"{i + 1}"
        cv2.circle(vis, (x + 8, max(14, y - 10)), 10, color, -1)
        _put(vis, badge, (x + 3, max(18, y - 5)), (15, 15, 15), 0.45, 1)
        _put(vis, f"{part.name} {part.confidence:.2f}", (x + 22, max(18, y - 4)), color, 0.45, 1)

    if current:
        cv2.drawMarker(vis, current, (40, 60, 255), cv2.MARKER_CROSS, 22, 2, cv2.LINE_AA)
        cv2.circle(vis, current, 16, (240, 240, 240), 2, cv2.LINE_AA)
        _put(vis, "TCP", (current[0] + 14, current[1] - 14), (80, 180, 255), 0.5, 1)

    bar = np.full((36, w, 3), 16, dtype=np.uint8)
    vis = np.vstack([bar, vis])
    status = f"AVM SORT   backend={backend}   parts={len(parts)}"
    if error_mm is not None:
        status += f"   err={error_mm:.2f}mm"
    if pick_index is not None and total_picks:
        status += f"   cycle={pick_index}/{total_picks}"
    cv2.putText(vis, status, (16, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 236, 242), 1, cv2.LINE_AA)
    return vis
