from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


LABELS = ("ok", "scratch", "crack", "notch")


@dataclass
class DefectBlob:
    contour: np.ndarray
    bbox: tuple[int, int, int, int]
    area: float
    features: np.ndarray


def extract_blob_features(gray: np.ndarray, contour: np.ndarray) -> np.ndarray:
    x, y, w, h = cv2.boundingRect(contour)
    area = float(cv2.contourArea(contour))
    peri = float(cv2.arcLength(contour, True)) + 1e-6
    rect_area = max(w * h, 1)
    extent = area / rect_area
    aspect = w / max(h, 1)
    hull = cv2.convexHull(contour)
    hull_area = max(float(cv2.contourArea(hull)), 1.0)
    solidity = area / hull_area
    circularity = 4.0 * np.pi * area / (peri * peri)

    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)
    mean, std = cv2.meanStdDev(gray, mask=mask)
    length = max(w, h) / max(gray.shape[0], 1)

    feats = np.array(
        [
            min(area / 4000.0, 3.0),
            min(aspect, 8.0) / 8.0,
            extent,
            float(mean[0][0]) / 255.0,
            float(std[0][0]) / 64.0,
            length,
            solidity,
            min(circularity, 2.0) / 2.0,
        ],
        dtype=np.float32,
    )
    return feats


def find_defect_blobs(mask: np.ndarray, gray: np.ndarray, min_area: int = 40) -> list[DefectBlob]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs: list[DefectBlob] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        blobs.append(
            DefectBlob(
                contour=cnt,
                bbox=tuple(cv2.boundingRect(cnt)),
                area=float(area),
                features=extract_blob_features(gray, cnt),
            )
        )
    blobs.sort(key=lambda b: b.area, reverse=True)
    return blobs
