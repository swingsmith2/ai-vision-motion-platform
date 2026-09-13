from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper, numpy_helper

from avm.ai.base import CLASS_COLORS, Detection, nms
from avm.ai.onnx_mlp import OnnxMLP

GRID_H = 7
GRID_W = 10
IN_W = 320
IN_H = 224
FEAT_DIM = 6
OUT_DIM = 8  # obj, cx, cy, w, h, 3 classes


def _cell_features(image: np.ndarray) -> np.ndarray:
    resized = cv2.resize(image, (IN_W, IN_H), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    ch, cw = IN_H // GRID_H, IN_W // GRID_W
    feats = np.zeros((GRID_H, GRID_W, FEAT_DIM), dtype=np.float32)
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            y0, x0 = gy * ch, gx * cw
            patch = resized[y0 : y0 + ch, x0 : x0 + cw]
            hp = hsv[y0 : y0 + ch, x0 : x0 + cw]
            mean = patch.reshape(-1, 3).mean(axis=0) / 255.0
            sat = hp[..., 1]
            vivid = sat > 70
            hue = float(hp[..., 0][vivid].mean()) / 180.0 if np.any(vivid) else 0.0
            feats[gy, gx] = [
                mean[0],
                mean[1],
                mean[2],
                hue,
                float(sat.mean()) / 255.0,
                float(vivid.mean()),
            ]
    return feats


def _crop_features(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x, y, bw, bh = bbox
    crop = image[max(y, 0) : y + bh, max(x, 0) : x + bw]
    if crop.size == 0:
        return np.zeros(FEAT_DIM, dtype=np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mean = crop.reshape(-1, 3).mean(axis=0) / 255.0
    sat = hsv[..., 1]
    vivid = sat > 70
    hue = float(hsv[..., 0][vivid].mean()) / 180.0 if np.any(vivid) else 0.0
    return np.array(
        [mean[0], mean[1], mean[2], hue, float(sat.mean()) / 255.0, float(vivid.mean())],
        dtype=np.float32,
    )


def _sat_proposals(image: np.ndarray, roi_top: int, min_area: int = 160) -> list[tuple[int, int, int, int]]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 70, 70), (179, 255, 255))
    mask[:roi_top, :] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        if cv2.contourArea(cnt) < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        boxes.append((x, y, w, h))
    return boxes


def _targets_from_parts(
    parts,
    image_w: int,
    image_h: int,
    names: tuple[str, ...],
    roi_top: int,
) -> np.ndarray:
    target = np.zeros((GRID_H, GRID_W, OUT_DIM), dtype=np.float32)
    name_to_id = {n: i for i, n in enumerate(names)}
    for part in parts:
        cx, cy = part.center
        if cy < roi_top:
            continue
        gx = int(np.clip(cx / image_w * GRID_W, 0, GRID_W - 1))
        gy = int(np.clip(cy / image_h * GRID_H, 0, GRID_H - 1))
        cls = name_to_id[part.name]
        target[gy, gx, 0] = 1.0
        target[gy, gx, 1] = cx / image_w
        target[gy, gx, 2] = cy / image_h
        target[gy, gx, 3] = part.size * 2.2 / image_w
        target[gy, gx, 4] = part.size * 2.2 / image_h
        target[gy, gx, 5 + cls] = 1.0
    return target


def train_tiny_yolo(
    scene_fn,
    names: tuple[str, ...],
    n_scenes: int = 48,
    roi_top: int = 120,
    seed: int = 3,
) -> tuple[OnnxMLP, OnnxMLP]:
    rng = np.random.default_rng(seed)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    cls_x: list[np.ndarray] = []
    cls_y: list[int] = []
    for i in range(n_scenes):
        img, parts = scene_fn(seed=int(rng.integers(0, 10_000)))
        feats = _cell_features(img)
        target = _targets_from_parts(parts, img.shape[1], img.shape[0], names, roi_top)
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                xs.append(feats[gy, gx])
                ys.append(target[gy, gx])
        name_to_id = {n: i for i, n in enumerate(names)}
        for part in parts:
            if part.center[1] < roi_top:
                continue
            vec = np.zeros(OUT_DIM, dtype=np.float32)
            vec[0] = 1.0
            vec[1] = part.center[0] / img.shape[1]
            vec[2] = part.center[1] / img.shape[0]
            vec[3] = part.size * 2.2 / img.shape[1]
            vec[4] = part.size * 2.2 / img.shape[0]
            vec[5 + name_to_id[part.name]] = 1.0
            xs.append(_crop_features(img, part.bbox))
            ys.append(vec)
            cls_x.append(_crop_features(img, part.bbox))
            cls_y.append(name_to_id[part.name])
    x = np.stack(xs)
    t = np.stack(ys)
    cls_mlp = OnnxMLP.train(
        np.stack(cls_x),
        np.array(cls_y, dtype=np.int64),
        names,
        hidden=24,
        lr=0.15,
        epochs=700,
    )
    return _train_regressor(x, t), cls_mlp


def _train_regressor(x: np.ndarray, t: np.ndarray, hidden: int = 32, lr: float = 0.06, epochs: int = 320) -> OnnxMLP:
    rng = np.random.default_rng(7)
    pos = np.where(t[:, 0] > 0.5)[0]
    neg = np.where(t[:, 0] <= 0.5)[0]
    rng.shuffle(neg)
    neg = neg[: max(len(pos) * 4, 80)]
    idx = np.concatenate([pos, neg])
    rng.shuffle(idx)
    xb = x[idx].astype(np.float64)
    tb = t[idx].astype(np.float64)

    n, d = xb.shape
    k = tb.shape[1]
    w1 = rng.normal(0, 0.25, size=(d, hidden))
    b1 = np.zeros(hidden)
    w2 = rng.normal(0, 0.25, size=(hidden, k))
    b2 = np.zeros(k)
    obj_mask = (tb[:, 0] > 0.5).astype(np.float64)[:, None]
    loss_w = np.ones_like(tb)
    loss_w[:, 1:] *= obj_mask
    loss_w[:, 0] *= 1.0 + 3.0 * tb[:, 0]

    for _ in range(epochs):
        h = np.maximum(xb @ w1 + b1, 0.0)
        y = h @ w2 + b2
        dz = ((y - tb) * loss_w) / n
        dw2 = h.T @ dz
        db2 = dz.sum(axis=0)
        dh = dz @ w2.T
        dh *= (h > 0).astype(np.float64)
        dw1 = xb.T @ dh
        db1 = dh.sum(axis=0)
        w2 -= lr * dw2
        b2 -= lr * db2
        w1 -= lr * dw1
        b1 -= lr * db1
    return OnnxMLP(w1=w1, b1=b1, w2=w2, b2=b2, labels=("raw",))


def export_tiny_yolo(mlp: OnnxMLP, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    w1 = mlp.w1.astype(np.float32)
    b1 = mlp.b1.astype(np.float32)
    w2 = mlp.w2.astype(np.float32)
    b2 = mlp.b2.astype(np.float32)
    x_in = helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, w1.shape[0]])
    y_out = helper.make_tensor_value_info("pred", TensorProto.FLOAT, [None, w2.shape[1]])
    graph = helper.make_graph(
        [
            helper.make_node("Gemm", ["features", "W1", "B1"], ["h1"], alpha=1.0, beta=1.0),
            helper.make_node("Relu", ["h1"], ["h1r"]),
            helper.make_node("Gemm", ["h1r", "W2", "B2"], ["pred"], alpha=1.0, beta=1.0),
        ],
        "avm_tiny_yolo",
        [x_in],
        [y_out],
        [
            numpy_helper.from_array(w1, name="W1"),
            numpy_helper.from_array(b1, name="B1"),
            numpy_helper.from_array(w2, name="W2"),
            numpy_helper.from_array(b2, name="B2"),
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 13)],
        ir_version=8,
        producer_name="avm-platform",
    )
    onnx.checker.check_model(model)
    onnx.save(model, str(path))
    return path


class TinyYoloDetector:
    """Grid + objectness + box + class, exported as ONNX. YOLO-style decode + NMS."""

    backend = "yolo-onnx"

    def __init__(
        self,
        model_path: str | Path,
        names: tuple[str, ...],
        obj_thr: float = 0.45,
        roi_top: int = 120,
        colors: dict | None = None,
        class_model_path: str | Path | None = None,
    ):
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.cls_session = (
            ort.InferenceSession(str(class_model_path), providers=["CPUExecutionProvider"])
            if class_model_path
            else None
        )
        self.cls_input = self.cls_session.get_inputs()[0].name if self.cls_session else None
        self.names = names
        self.obj_thr = obj_thr
        self.roi_top = roi_top
        self.colors = colors or CLASS_COLORS

    def infer(self, image: np.ndarray) -> list[Detection]:
        dets: list[Detection] = []
        boxes = _sat_proposals(image, self.roi_top)
        if boxes:
            feats = np.stack([_crop_features(image, b) for b in boxes]).astype(np.float32)
            pred = self.session.run(None, {self.input_name: feats})[0]
            if self.cls_session is not None:
                cls_logits = self.cls_session.run(None, {self.cls_input: feats})[0]
            else:
                cls_logits = pred[:, 5 : 5 + len(self.names)]
            for bbox, row, clog, feat in zip(boxes, pred, cls_logits, feats):
                obj = float(np.clip(row[0], 0.0, 1.5))
                cls = int(np.argmax(clog))
                conf = float(np.exp(clog[cls] - np.max(clog)) / np.exp(clog - np.max(clog)).sum())
                if obj < self.obj_thr and conf < 0.55:
                    continue
                x, y, bw, bh = bbox
                name = self.names[cls]
                hue = float(feat[3])
                if name in {"washer", "nut"}:
                    name = "nut" if hue < 0.125 else "washer"
                dets.append(
                    Detection(
                        name=name,
                        confidence=float(np.clip(max(obj, conf), 0.0, 1.0)),
                        bbox=bbox,
                        centroid=(x + bw / 2, y + bh / 2),
                        backend=self.backend,
                        color_bgr=tuple(self.colors.get(name, (200, 200, 200))),
                    )
                )
        dets = nms(dets, iou_thr=0.25)
        dets = _center_nms(dets, min_dist=52)
        dets.sort(key=lambda d: (d.centroid[1], d.centroid[0]))
        return dets


def _center_nms(dets: list[Detection], min_dist: float) -> list[Detection]:
    kept: list[Detection] = []
    for det in sorted(dets, key=lambda d: d.confidence, reverse=True):
        if all(((det.centroid[0] - k.centroid[0]) ** 2 + (det.centroid[1] - k.centroid[1]) ** 2) ** 0.5 >= min_dist for k in kept):
            kept.append(det)
    return kept


class UltralyticsYoloDetector:
    backend = "ultralytics"

    def __init__(
        self,
        model: str,
        names: tuple[str, ...],
        conf: float = 0.25,
        roi_top: int = 120,
        colors: dict | None = None,
    ):
        from ultralytics import YOLO

        self.model = YOLO(model)
        self.names = names
        self.conf = conf
        self.roi_top = roi_top
        self.colors = colors or CLASS_COLORS

    def infer(self, image: np.ndarray) -> list[Detection]:
        result = self.model.predict(image, conf=self.conf, verbose=False)[0]
        dets: list[Detection] = []
        if result.boxes is None:
            return dets
        for box in result.boxes:
            cls = int(box.cls.item())
            if isinstance(self.model.names, dict):
                name = self.model.names.get(cls, self.names[cls] if cls < len(self.names) else str(cls))
            else:
                name = self.names[cls] if cls < len(self.names) else str(cls)
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            cy = (y1 + y2) / 2
            if cy < self.roi_top:
                continue
            dets.append(
                Detection(
                    name=name,
                    confidence=float(box.conf.item()),
                    bbox=(int(x1), int(y1), int(x2 - x1), int(y2 - y1)),
                    centroid=((x1 + x2) / 2, (y1 + y2) / 2),
                    backend=self.backend,
                    color_bgr=tuple(self.colors.get(name, CLASS_COLORS.get(name, (200, 200, 200)))),
                )
            )
        return dets
