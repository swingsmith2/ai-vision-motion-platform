from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


CLASS_COLORS = {
    "washer": (0, 220, 230),
    "nut": (30, 140, 230),
    "block": (230, 160, 40),
}


@dataclass
class Detection:
    name: str
    confidence: float
    bbox: tuple[int, int, int, int]
    centroid: tuple[float, float]
    backend: str
    color_bgr: tuple[int, int, int] = (200, 200, 200)

    @property
    def score(self) -> float:
        return self.confidence


class ObjectDetector(Protocol):
    backend: str

    def infer(self, image: np.ndarray) -> list[Detection]:
        ...


def nms(dets: list[Detection], iou_thr: float = 0.45) -> list[Detection]:
    if not dets:
        return []
    boxes = np.array(
        [[d.bbox[0], d.bbox[1], d.bbox[0] + d.bbox[2], d.bbox[1] + d.bbox[3]] for d in dets],
        dtype=np.float32,
    )
    scores = np.array([d.confidence for d in dets], dtype=np.float32)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / np.maximum(area_i + area_r - inter, 1e-6)
        order = rest[iou <= iou_thr]
    return [dets[i] for i in keep]
