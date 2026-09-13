from __future__ import annotations

import cv2
import numpy as np


def enhance_metal(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(blur)


def isolate_defects(image: np.ndarray) -> np.ndarray:
    enhanced = enhance_metal(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    blackhat = cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel)
    tophat = cv2.morphologyEx(enhanced, cv2.MORPH_TOPHAT, kernel)
    fused = cv2.addWeighted(blackhat, 0.70, tophat, 0.30, 0)
    fused = cv2.GaussianBlur(fused, (3, 3), 0)
    thr = max(float(np.percentile(fused, 99.3)), 22.0)
    _, mask = cv2.threshold(fused, thr, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return mask


def find_edge_void(image: np.ndarray, dark_thr: int = 36, min_area: int = 180) -> tuple[int, int, int, int] | None:
    """Detect missing material that touches the image border (notch / chip)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    dark = (gray < dark_thr).astype(np.uint8) * 255
    h, w = gray.shape
    margin = 8
    border = np.zeros_like(dark)
    border[:margin, :] = 255
    border[-margin:, :] = 255
    border[:, :margin] = 255
    border[:, -margin:] = 255
    num, labels, stats, _ = cv2.connectedComponentsWithStats(dark)
    best = None
    best_area = 0
    for i in range(1, num):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        comp = np.zeros_like(dark)
        comp[labels == i] = 255
        if cv2.countNonZero(cv2.bitwise_and(comp, border)) == 0:
            continue
        if area > best_area:
            best_area = area
            best = (
                int(stats[i, cv2.CC_STAT_LEFT]),
                int(stats[i, cv2.CC_STAT_TOP]),
                int(stats[i, cv2.CC_STAT_WIDTH]),
                int(stats[i, cv2.CC_STAT_HEIGHT]),
            )
    return best
