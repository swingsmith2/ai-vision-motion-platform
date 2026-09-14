from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class LineObservation:
    found: bool
    e_y_px: float = 0.0
    e_theta_rad: float = 0.0
    x_near: float = 0.0
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0
    score: float = 0.0


def _line_x_at(x1: float, y1: float, x2: float, y2: float, y: float) -> float:
    if abs(y2 - y1) < 1e-6:
        return 0.5 * (x1 + x2)
    t = (y - y1) / (y2 - y1)
    return x1 + t * (x2 - x1)


def detect_aluminum_line(
    image: np.ndarray,
    *,
    prev_x: float | None = None,
    max_angle_deg: float = 22.0,
    roi_top_ratio: float = 0.28,
) -> LineObservation:
    """Detect the nearest longitudinal aluminum frame in a downward camera view."""
    h, w = image.shape[:2]
    y0 = int(h * roi_top_ratio)
    roi = image[y0:h, :].copy()
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    silver = cv2.inRange(hsv, (0, 0, 145), (180, 70, 255))
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 17))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    _, bright = cv2.threshold(tophat, max(18, float(np.percentile(tophat, 92))), 255, cv2.THRESH_BINARY)
    mask = cv2.bitwise_or(silver, bright.astype(np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    lines = cv2.HoughLinesP(mask, 1, np.pi / 180.0, threshold=20, minLineLength=28, maxLineGap=18)
    if lines is None:
        return LineObservation(found=False)

    candidates: list[LineObservation] = []
    max_rad = np.deg2rad(max_angle_deg)
    y_near = roi.shape[0] * 0.82
    for item in lines.reshape(-1, 4):
        x1, y1, x2, y2 = (int(v) for v in item)
        dy = y2 - y1
        dx = x2 - x1
        if abs(dy) < 8:
            continue
        theta = float(np.arctan2(dx, dy))
        if abs(theta) > max_rad:
            continue
        x_near = _line_x_at(x1, y1, x2, y2, y_near)
        candidates.append(
            LineObservation(
                found=True,
                e_y_px=float(x_near - w * 0.5),
                e_theta_rad=theta,
                x_near=float(x_near),
                x1=x1,
                y1=y1 + y0,
                x2=x2,
                y2=y2 + y0,
                score=float(-abs(x_near - (prev_x if prev_x is not None else w * 0.5))),
            )
        )
    if not candidates:
        col = mask.sum(axis=0).astype(np.float32)
        k = np.ones(9, dtype=np.float32) / 9.0
        col = np.convolve(col, k, mode="same")
        peak = int(np.argmax(col))
        if col[peak] > 400:
            candidates.append(
                LineObservation(
                    found=True,
                    e_y_px=float(peak) - w * 0.5,
                    e_theta_rad=0.0,
                    x_near=float(peak),
                    x1=peak,
                    y1=y0 + 8,
                    x2=peak,
                    y2=h - 8,
                )
            )
    if not candidates:
        return LineObservation(found=False)

    def pick(target: float, max_dist: float) -> LineObservation | None:
        nearby = [c for c in candidates if abs(c.x_near - target) <= max_dist]
        if not nearby:
            return None
        return min(nearby, key=lambda c: abs(c.x_near - target) + 20.0 * abs(c.e_theta_rad))

    if prev_x is not None:
        hit = pick(prev_x, 40.0) or pick(w * 0.5, 55.0)
    else:
        hit = pick(w * 0.5, 55.0)
    return hit or LineObservation(found=False)
