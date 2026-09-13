from __future__ import annotations

import numpy as np

from avm.vision.calibration import CameraCalibration


def pixel_to_world(u: float, v: float, calib: CameraCalibration) -> tuple[float, float]:
    p = np.array([u, v, 1.0], dtype=np.float64)
    w = calib.homography @ p
    w /= w[2]
    return float(w[0]), float(w[1])


def world_to_pixel(x: float, y: float, calib: CameraCalibration) -> tuple[float, float]:
    inv = np.linalg.inv(calib.homography)
    p = inv @ np.array([x, y, 1.0], dtype=np.float64)
    p /= p[2]
    return float(p[0]), float(p[1])
