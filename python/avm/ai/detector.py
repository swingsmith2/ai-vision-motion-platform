from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from avm.ai.base import Detection
from avm.ai.features import DefectBlob, find_defect_blobs
from avm.ai.image_features import extract_image_features, localize_defect
from avm.ai.onnx_mlp import OnnxRuntimeClassifier
from avm.vision.preprocess import enhance_metal, find_edge_void, isolate_defects


@dataclass
class DefectResult:
    label: str
    confidence: float
    ok: bool
    bbox: tuple[int, int, int, int] | None
    features: list[float] = field(default_factory=list)
    reason: str = ""


class DefectDetector:
    def __init__(
        self,
        classifier: OnnxRuntimeClassifier,
        min_area: int = 80,
        min_conf: float = 0.45,
        ok_area: float = 90.0,
    ):
        self.classifier = classifier
        self.min_area = min_area
        self.min_conf = min_conf
        self.ok_area = ok_area

    def infer(self, image: np.ndarray) -> DefectResult:
        void = find_edge_void(image)
        if void is not None:
            return DefectResult(
                label="notch",
                confidence=0.93,
                ok=False,
                bbox=void,
                reason="border void / missing material",
            )
        gray = enhance_metal(image)
        mask = isolate_defects(image)
        blobs = find_defect_blobs(mask, gray, min_area=self.min_area)
        if not blobs or blobs[0].area < self.ok_area:
            return DefectResult(label="ok", confidence=0.97, ok=True, bbox=None, reason="no significant defect blob")

        blob = blobs[0]
        idx, conf = self.classifier.predict(blob.features.reshape(1, -1))
        label = self.classifier.labels[int(idx[0])]
        confidence = float(conf[0])
        ok = label == "ok"
        reason = "classified"
        if not ok and confidence < self.min_conf:
            reason = "low-confidence defect, send to review/reject"
        return DefectResult(
            label=label,
            confidence=confidence,
            ok=ok,
            bbox=blob.bbox,
            features=blob.features.tolist(),
            reason=reason,
        )


class ImageDefectDetector:
    """Image-level ONNX classifier for public industrial datasets such as NEU-CLS."""

    def __init__(self, classifier: OnnxRuntimeClassifier, ok_labels: tuple[str, ...] = ("ok",)):
        self.classifier = classifier
        self.ok_labels = set(ok_labels)

    def infer(self, image: np.ndarray) -> DefectResult:
        feat = extract_image_features(image)
        idx, conf = self.classifier.predict(feat.reshape(1, -1))
        label = self.classifier.labels[int(idx[0])]
        return DefectResult(
            label=label,
            confidence=float(conf[0]),
            ok=label in self.ok_labels,
            bbox=localize_defect(image),
            features=feat.tolist(),
            reason="image-level ONNX classification",
        )


@dataclass
class DetectedPart:
    name: str
    color_bgr: tuple[int, int, int]
    centroid_px: tuple[float, float]
    bbox: tuple[int, int, int, int]
    contour: np.ndarray
    score: float


class PartDetector:
    """Color + shape detector for the simulated sorting cell."""

    backend = "opencv"

    def __init__(self, classes: dict, roi_top: int = 120):
        self.classes = classes
        self.roi_top = roi_top

    def infer(self, image: np.ndarray) -> list[DetectedPart]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        parts: list[DetectedPart] = []
        for name, spec in self.classes.items():
            low = np.array(spec["hsv_low"], dtype=np.uint8)
            high = np.array(spec["hsv_high"], dtype=np.uint8)
            mask = cv2.inRange(hsv, low, high)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < spec.get("min_area", 200):
                    continue
                M = cv2.moments(cnt)
                if M["m00"] < 1:
                    continue
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                if cy < self.roi_top:
                    continue
                shape = spec.get("shape", "any")
                if not _shape_ok(cnt, shape):
                    continue
                parts.append(
                    DetectedPart(
                        name=name,
                        color_bgr=tuple(spec["draw_bgr"]),
                        centroid_px=(cx, cy),
                        bbox=tuple(cv2.boundingRect(cnt)),
                        contour=cnt,
                        score=min(1.0, area / 2500.0),
                    )
                )
        parts.sort(key=lambda p: (p.centroid_px[1], p.centroid_px[0]))
        return parts


class OpenCvPartDetector(PartDetector):
    """Same as PartDetector, but returns the unified Detection type."""

    def infer(self, image: np.ndarray) -> list[Detection]:
        parts = super().infer(image)
        return [
            Detection(
                name=p.name,
                confidence=float(p.score),
                bbox=p.bbox,
                centroid=p.centroid_px,
                backend=self.backend,
                color_bgr=p.color_bgr,
            )
            for p in parts
        ]


def _shape_ok(cnt: np.ndarray, shape: str) -> bool:
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
    area = cv2.contourArea(cnt)
    if area < 1:
        return False
    (x, y, w, h) = cv2.boundingRect(cnt)
    extent = area / max(w * h, 1)
    if shape == "circle":
        return len(approx) >= 6 and extent > 0.60
    if shape == "hex":
        return 5 <= len(approx) <= 8
    if shape == "rect":
        return len(approx) <= 6 and 0.55 < (w / max(h, 1)) < 1.80
    return True
