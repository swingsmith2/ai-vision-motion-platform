from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CameraCalibration:
    """Pinhole + table-plane homography. Units: pixels and meters."""

    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    homography: np.ndarray  # 3x3, pixel -> world (x, y, 1)

    @classmethod
    def synthetic_topdown(cls, width: int, height: int, table_w: float, table_h: float) -> "CameraCalibration":
        src = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float64,
        )
        dst = np.array(
            [[0.0, 0.0], [table_w, 0.0], [table_w, table_h], [0.0, table_h]],
            dtype=np.float64,
        )
        import cv2

        H = cv2.getPerspectiveTransform(src.astype(np.float32), dst.astype(np.float32))
        return cls(
            width=width,
            height=height,
            fx=0.8 * width,
            fy=0.8 * width,
            cx=width / 2.0,
            cy=height / 2.0,
            homography=H,
        )

    @property
    def K(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
