from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

NEU_LABELS = (
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled_in_scale",
    "scratches",
)

PREFIX_TO_LABEL = {
    "Cr": "crazing",
    "In": "inclusion",
    "Pa": "patches",
    "PS": "pitted_surface",
    "RS": "rolled_in_scale",
    "Sc": "scratches",
}

DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "NEU-CLS"


@dataclass
class Sample:
    path: Path
    label: str


def load_neu_cls(root: Path | None = None) -> list[Sample]:
    root = Path(root) if root else DEFAULT_ROOT
    if not root.exists():
        raise FileNotFoundError(f"NEU-CLS not found at {root}")
    samples: list[Sample] = []
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".bmp", ".png", ".jpg", ".jpeg"}:
            continue
        prefix = path.stem.split("_", 1)[0]
        label = PREFIX_TO_LABEL.get(prefix)
        if label is None:
            continue
        samples.append(Sample(path=path, label=label))
    samples.sort(key=lambda s: (s.label, s.path.name))
    if not samples:
        raise FileNotFoundError(f"no NEU-CLS images under {root}")
    return samples


def split_dataset(samples: list[Sample], val_ratio: float = 0.2, seed: int = 7) -> tuple[list[Sample], list[Sample]]:
    by_label: dict[str, list[Sample]] = {}
    for s in samples:
        by_label.setdefault(s.label, []).append(s)
    rng = random.Random(seed)
    train: list[Sample] = []
    val: list[Sample] = []
    for label in NEU_LABELS:
        items = by_label.get(label, [])
        rng.shuffle(items)
        n_val = max(1, int(len(items) * val_ratio))
        val.extend(items[:n_val])
        train.extend(items[n_val:])
    return train, val
