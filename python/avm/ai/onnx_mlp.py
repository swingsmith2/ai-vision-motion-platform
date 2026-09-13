from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper, numpy_helper


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _one_hot(y: np.ndarray, n: int) -> np.ndarray:
    out = np.zeros((y.shape[0], n), dtype=np.float64)
    out[np.arange(y.shape[0]), y] = 1.0
    return out


@dataclass
class OnnxMLP:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray
    labels: tuple[str, ...]

    @classmethod
    def train(
        cls,
        x: np.ndarray,
        y: np.ndarray,
        labels: tuple[str, ...],
        hidden: int = 16,
        lr: float = 0.08,
        epochs: int = 400,
        seed: int = 7,
    ) -> "OnnxMLP":
        rng = np.random.default_rng(seed)
        n, d = x.shape
        k = len(labels)
        w1 = rng.normal(0, 0.35, size=(d, hidden))
        b1 = np.zeros(hidden)
        w2 = rng.normal(0, 0.35, size=(hidden, k))
        b2 = np.zeros(k)
        xb = x.astype(np.float64)
        yoh = _one_hot(y.astype(int), k)

        for _ in range(epochs):
            h = _relu(xb @ w1 + b1)
            p = _softmax(h @ w2 + b2)
            dz = (p - yoh) / n
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
        return cls(w1=w1, b1=b1, w2=w2, b2=b2, labels=labels)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        h = _relu(x.astype(np.float64) @ self.w1 + self.b1)
        return _softmax(h @ self.w2 + self.b2)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.predict_proba(x).argmax(axis=1)

    def export_onnx(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        w1 = self.w1.astype(np.float32)
        b1 = self.b1.astype(np.float32)
        w2 = self.w2.astype(np.float32)
        b2 = self.b2.astype(np.float32)

        x_in = helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, w1.shape[0]])
        y_out = helper.make_tensor_value_info("logits", TensorProto.FLOAT, [None, w2.shape[1]])
        nodes = [
            helper.make_node("Gemm", ["features", "W1", "B1"], ["h1"], alpha=1.0, beta=1.0),
            helper.make_node("Relu", ["h1"], ["h1r"]),
            helper.make_node("Gemm", ["h1r", "W2", "B2"], ["logits"], alpha=1.0, beta=1.0),
        ]
        graph = helper.make_graph(
            nodes,
            "avm_defect_mlp",
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


class OnnxRuntimeClassifier:
    def __init__(self, model_path: str | Path, labels: tuple[str, ...]):
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.labels = labels
        self.input_name = self.session.get_inputs()[0].name

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        logits = self.session.run(None, {self.input_name: x.astype(np.float32)})[0]
        logits = logits - logits.max(axis=1, keepdims=True)
        e = np.exp(logits)
        return e / e.sum(axis=1, keepdims=True)

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        proba = self.predict_proba(x)
        idx = proba.argmax(axis=1)
        return idx, proba.max(axis=1)
