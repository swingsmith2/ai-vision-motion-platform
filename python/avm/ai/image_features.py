from __future__ import annotations

import cv2
import numpy as np

from avm.vision.preprocess import enhance_metal, isolate_defects


def extract_image_features(image: np.ndarray) -> np.ndarray:
    """Texture + morphology features for steel-surface defect classification."""
    gray = enhance_metal(image)
    hist = cv2.calcHist([gray], [0], None, [8], [0, 256]).flatten()
    hist = hist / max(float(hist.sum()), 1.0)
    lbp = _lbp_hist(gray)
    mean = float(gray.mean()) / 255.0
    std = float(gray.std()) / 64.0
    p10, p90 = np.percentile(gray, [10, 90]) / 255.0
    edges = cv2.Canny(gray, 60, 140)
    edge_density = float(np.count_nonzero(edges)) / gray.size
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 2000.0
    mask = isolate_defects(image)
    blob_density = float(np.count_nonzero(mask)) / mask.size
    num, _, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8))
    max_area = float(stats[1:, cv2.CC_STAT_AREA].max()) / gray.size if num > 1 else 0.0
    return np.concatenate(
        [
            hist.astype(np.float32),
            lbp.astype(np.float32),
            np.array(
                [mean, std, float(p10), float(p90), edge_density, lap_var, blob_density, max_area],
                dtype=np.float32,
            ),
        ]
    )


def localize_defect(image: np.ndarray) -> tuple[int, int, int, int] | None:
    mask = isolate_defects(image)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 20:
        return None
    return tuple(cv2.boundingRect(cnt))


def _lbp_hist(gray: np.ndarray) -> np.ndarray:
    g = gray.astype(np.int16)
    h, w = g.shape
    if h < 3 or w < 3:
        return np.zeros(8, dtype=np.float32)
    center = g[1:-1, 1:-1]
    codes = np.zeros(center.shape, dtype=np.uint8)
    offsets = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1))
    for i, (dy, dx) in enumerate(offsets):
        neigh = g[1 + dy : h - 1 + dy, 1 + dx : w - 1 + dx]
        codes |= ((neigh >= center) << i).astype(np.uint8)
    hist, _ = np.histogram(codes, bins=8, range=(0, 256), density=True)
    return hist.astype(np.float32)
