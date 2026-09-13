from __future__ import annotations

import sys
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "apps") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps"))
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

from sorter.generate_scene import make_scene

NAMES = ("washer", "nut", "block")
OFFICIAL_WEIGHTS = "yolov8n.pt"


def _yolo_line(bbox: tuple[int, int, int, int], cls: int, width: int, height: int) -> str:
    x, y, w, h = bbox
    cx = (x + w / 2) / width
    cy = (y + h / 2) / height
    nw = w / width
    nh = h / height
    return f"{cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"


def export_sorter_yolo_dataset(
    out_dir: Path,
    width: int = 800,
    height: int = 560,
    n_train: int = 64,
    n_val: int = 16,
    seed: int = 11,
) -> Path:
    out_dir = Path(out_dir)
    name_to_id = {n: i for i, n in enumerate(NAMES)}
    for split, n, offset in (("train", n_train, 0), ("val", n_val, 10_000)):
        img_dir = out_dir / "images" / split
        lab_dir = out_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lab_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            scene, parts = make_scene(width, height, seed=seed + offset + i)
            stem = f"{split}_{i:03d}"
            cv2.imwrite(str(img_dir / f"{stem}.png"), scene)
            lines = [_yolo_line(p.bbox, name_to_id[p.name], width, height) for p in parts]
            (lab_dir / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    data_yaml = out_dir / "data.yaml"
    payload = {
        "path": str(out_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {i: n for i, n in enumerate(NAMES)},
        "nc": len(NAMES),
    }
    data_yaml.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return data_yaml


def download_official_weights(dest: Path, name: str = OFFICIAL_WEIGHTS) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if target.exists() and target.stat().st_size > 1_000_000:
        return target
    from ultralytics.utils.downloads import attempt_download_asset

    src = Path(attempt_download_asset(name))
    if src.exists() and src.resolve() != target.resolve():
        target.write_bytes(src.read_bytes())
    elif src.exists():
        return src
    if not target.exists():
        raise FileNotFoundError(f"failed to download {name}")
    return target


def finetune_yolov8(
    data_yaml: Path,
    base_weights: Path,
    project: Path,
    epochs: int = 12,
    imgsz: int = 416,
    batch: int = 8,
) -> Path:
    from ultralytics import YOLO

    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    best = project / "sorter" / "weights" / "best.pt"
    if best.exists() and best.stat().st_size > 1_000_000:
        return best

    model = YOLO(str(base_weights))
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=str(project),
        name="sorter",
        exist_ok=True,
        workers=0,
        amp=False,
        device="cpu",
        patience=8,
        verbose=True,
    )
    if not best.exists():
        raise FileNotFoundError(f"YOLOv8 training finished but {best} is missing")
    return best


def export_onnx(weights: Path, out_path: Path) -> Path:
    from ultralytics import YOLO

    model = YOLO(str(weights))
    exported = model.export(format="onnx", imgsz=416, simplify=True, opset=12)
    src = Path(exported)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.exists() and src.resolve() != out_path.resolve():
        out_path.write_bytes(src.read_bytes())
        return out_path
    return src
