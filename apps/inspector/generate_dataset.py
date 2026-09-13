from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from avm.ai.features import LABELS, extract_blob_features, find_defect_blobs
from avm.vision.preprocess import enhance_metal, isolate_defects


def _metal_base(rng: np.random.Generator, size: int = 320) -> np.ndarray:
    noise = rng.normal(118, 14, (size, size)).astype(np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    grain = 8 * np.sin(xx / 3.2) + 4 * np.sin(yy / 17.0)
    img = np.clip(noise + grain, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def _draw_scratch(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape[:2]
    pts = np.array(
        [[rng.integers(30, w - 30), rng.integers(30, h - 30)] for _ in range(rng.integers(3, 5))],
        dtype=np.int32,
    )
    color = (int(rng.integers(210, 245)),) * 3
    cv2.polylines(img, [pts], False, color, thickness=2, lineType=cv2.LINE_AA)
    return img


def _draw_crack(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape[:2]
    x = int(rng.integers(40, w - 40))
    y = int(rng.integers(40, h - 40))
    pts = [[x, y]]
    for _ in range(int(rng.integers(5, 8))):
        x = int(np.clip(x + rng.integers(-18, 19), 10, w - 10))
        y = int(np.clip(y + rng.integers(8, 22), 10, h - 10))
        pts.append([x, y])
    cv2.polylines(img, [np.array(pts, dtype=np.int32)], False, (10, 10, 10), 3, cv2.LINE_AA)
    return img


def _draw_notch(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape[:2]
    side = int(rng.integers(0, 4))
    r = int(rng.integers(22, 36))
    if side == 0:
        c = (int(rng.integers(40, w - 40)), 0)
    elif side == 1:
        c = (int(rng.integers(40, w - 40)), h - 1)
    elif side == 2:
        c = (0, int(rng.integers(40, h - 40)))
    else:
        c = (w - 1, int(rng.integers(40, h - 40)))
    cv2.circle(img, c, r, (8, 8, 8), -1)
    return img


def synthesize(label: str, rng: np.random.Generator, size: int = 320) -> np.ndarray:
    img = _metal_base(rng, size)
    if label == "scratch":
        img = _draw_scratch(img, rng)
    elif label == "crack":
        img = _draw_crack(img, rng)
    elif label == "notch":
        img = _draw_notch(img, rng)
    return img


def collect_training_vectors(n_per_class: int, seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    xs: list[np.ndarray] = []
    ys: list[int] = []
    for idx, label in enumerate(LABELS):
        for _ in range(n_per_class):
            img = synthesize(label, rng)
            gray = enhance_metal(img)
            mask = isolate_defects(img)
            blobs = find_defect_blobs(mask, gray, min_area=50)
            if label == "ok":
                feat = np.array([0.02, 0.10, 0.12, 0.46, 0.08, 0.03, 0.95, 0.60], dtype=np.float32)
                if blobs and blobs[0].area < 70:
                    feat = blobs[0].features
            else:
                if not blobs:
                    feat = extract_blob_features(gray, np.array([[[40, 40]], [[90, 46]], [[82, 78]]], np.int32))
                else:
                    feat = blobs[0].features
            xs.append(feat)
            ys.append(idx)
    return np.stack(xs), np.array(ys, dtype=np.int64)


def write_eval_images(out_dir: Path, n_per_class: int = 8, seed: int = 21) -> list[dict]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    k = 0
    for label in LABELS:
        for i in range(n_per_class):
            img = synthesize(label, rng)
            name = f"{k:03d}_{label}.png"
            path = out_dir / name
            cv2.imwrite(str(path), img)
            items.append({"id": f"{k:03d}", "file": name, "label": label})
            k += 1
    (out_dir / "manifest.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    return items
