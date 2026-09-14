from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PvWorld:
    image: np.ndarray
    seam_xs: list[int]
    panel_w: int
    panel_h: int
    mm_per_px: float


def render_pv_array(
    width: int = 720,
    height: int = 1280,
    panel_w: int = 96,
    panel_h: int = 160,
    frame: int = 7,
    mm_per_px: float = 10.0,
    seed: int = 3,
) -> PvWorld:
    rng = np.random.default_rng(seed)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (42, 36, 28)
    origin_x = 48
    origin_y = 36
    seam_xs: list[int] = []
    x = origin_x
    while x + frame < width - 24:
        seam_xs.append(x)
        x += panel_w
    seam_xs.append(x)

    for i, sx in enumerate(seam_xs[:-1]):
        for sy in range(origin_y, height - 40, panel_h):
            x0, y0 = sx, sy
            x1, y1 = min(width - 8, sx + panel_w), min(height - 8, sy + panel_h)
            glass = (58 + int(rng.integers(-6, 7)), 78 + int(rng.integers(-8, 8)), 46 + int(rng.integers(-4, 5)))
            cv2.rectangle(img, (x0, y0), (x1, y1), glass, -1)
            cell = 18
            for cy in range(y0 + 10, y1 - 8, cell):
                cv2.line(img, (x0 + 6, cy), (x1 - 6, cy), (glass[0] + 8, glass[1] + 10, glass[2] + 6), 1)
            for cx in range(x0 + 12, x1 - 8, cell):
                cv2.line(img, (cx, y0 + 8), (cx, y1 - 8), (glass[0] + 6, glass[1] + 8, glass[2] + 4), 1)
            if rng.random() < 0.18:
                dx = int(rng.integers(x0 + 12, max(x0 + 13, x1 - 16)))
                dy = int(rng.integers(y0 + 16, max(y0 + 17, y1 - 16)))
                cv2.circle(img, (dx, dy), int(rng.integers(3, 7)), (30, 34, 38), -1)

    silver = (198, 196, 188)
    for sx in seam_xs:
        cv2.line(img, (sx, origin_y), (sx, height - 24), silver, frame)
        highlight = (230, 228, 220)
        cv2.line(img, (sx, origin_y), (sx, height - 24), highlight, 1)
    for sy in range(origin_y, height - 24, panel_h):
        cv2.line(img, (origin_x, sy), (seam_xs[-1], sy), silver, frame - 1)

    for _ in range(5):
        gx = int(rng.integers(80, width - 80))
        gy = int(rng.integers(80, height - 80))
        overlay = img.copy()
        cv2.ellipse(overlay, (gx, gy), (28, 12), float(rng.uniform(-20, 20)), 0, 360, (245, 245, 240), -1)
        img = cv2.addWeighted(overlay, 0.18, img, 0.82, 0)

    return PvWorld(img, seam_xs, panel_w, panel_h, mm_per_px)


def camera_view(
    world: np.ndarray,
    x: float,
    y: float,
    theta: float,
    cam_w: int = 320,
    cam_h: int = 240,
    robot_v: float | None = None,
) -> np.ndarray:
    """Downward camera: heading faces image up, robot near the bottom. No left-right flip."""
    if robot_v is None:
        robot_v = cam_h - 36
    c, s = np.cos(theta), np.sin(theta)
    cx, rv = cam_w * 0.5, robot_v
    m_dst_to_src = np.array(
        [
            [c, -s, x - c * cx + s * rv],
            [-s, -c, y + s * cx + c * rv],
        ],
        dtype=np.float32,
    )
    m = cv2.invertAffineTransform(m_dst_to_src)
    return cv2.warpAffine(
        world, m, (cam_w, cam_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(32, 28, 22)
    )
