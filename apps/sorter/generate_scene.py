from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ScenePart:
    name: str
    color_bgr: tuple[int, int, int]
    center: tuple[int, int]
    size: int
    bbox: tuple[int, int, int, int]


def _hex_points(cx: int, cy: int, r: int) -> np.ndarray:
    pts = []
    for i in range(6):
        a = math.radians(30 + i * 60)
        pts.append([int(cx + r * math.cos(a)), int(cy + r * math.sin(a))])
    return np.array(pts, dtype=np.int32)


def make_scene(width: int, height: int, seed: int = 5) -> tuple[np.ndarray, list[ScenePart]]:
    rng = np.random.default_rng(seed)
    img = np.full((height, width, 3), 34, dtype=np.uint8)
    img[:] = (38, 36, 32)
    for y in range(0, height, 18):
        cv2.line(img, (0, y), (width, y), (46, 44, 40), 1)

    bins = [
        ("A washer", (0, 220, 230), (70, 52)),
        ("B nut", (30, 140, 230), (width // 2, 52)),
        ("C block", (230, 160, 40), (width - 70, 52)),
    ]
    for label, color, (bx, by) in bins:
        cv2.rectangle(img, (bx - 48, by - 28), (bx + 48, by + 28), color, 2)
        cv2.putText(img, label, (bx - 44, by + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    catalog = [
        ("washer", (0, 220, 230), "circle"),
        ("nut", (30, 140, 230), "hex"),
        ("block", (230, 160, 40), "rect"),
    ]
    parts: list[ScenePart] = []
    occupied: list[tuple[int, int, int]] = []
    for i in range(7):
        name, color, shape = catalog[i % 3]
        for _ in range(40):
            cx = int(rng.integers(90, width - 90))
            cy = int(rng.integers(150, height - 70))
            if all(math.hypot(cx - ox, cy - oy) > 70 for ox, oy, _ in occupied):
                occupied.append((cx, cy, 28))
                if shape == "circle":
                    cv2.circle(img, (cx, cy), 18, color, -1)
                    cv2.circle(img, (cx, cy), 7, (38, 36, 32), -1)
                    bbox = (cx - 18, cy - 18, 36, 36)
                elif shape == "hex":
                    cv2.fillPoly(img, [_hex_points(cx, cy, 20)], color)
                    bbox = (cx - 20, cy - 20, 40, 40)
                else:
                    cv2.rectangle(img, (cx - 16, cy - 12), (cx + 16, cy + 12), color, -1)
                    bbox = (cx - 16, cy - 12, 32, 24)
                parts.append(ScenePart(name, color, (cx, cy), 22, bbox))
                break
    return img, parts
