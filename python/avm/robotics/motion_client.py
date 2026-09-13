from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MotionResult:
    samples: list[dict]
    final_error: float
    path: list[tuple[float, float]]


class MotionClient:
    def __init__(self, binary: Path, workdir: Path):
        self.binary = Path(binary)
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def plan_and_follow(
        self,
        waypoints: list[tuple[float, float]],
        job_name: str,
        vmax: float = 0.35,
        amax: float = 1.1,
        kp: float = 80.0,
        ki: float = 8.0,
        kd: float = 6.0,
        dt: float = 0.002,
    ) -> MotionResult:
        job = self.workdir / f"{job_name}.txt"
        csv_path = self.workdir / f"{job_name}.csv"
        lines = [
            f"vmax={vmax}",
            f"amax={amax}",
            f"dt={dt}",
            f"pid kp={kp} ki={ki} kd={kd}",
        ]
        for x, y in waypoints:
            lines.append(f"waypoint {x:.5f},{y:.5f}")
        job.write_text("\n".join(lines) + "\n", encoding="utf-8")

        proc = subprocess.run(
            [str(self.binary), str(job), str(csv_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"avm-motion failed: {proc.stderr}")

        samples: list[dict] = []
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                samples.append({k: float(v) for k, v in row.items()})
        if not samples:
            raise RuntimeError("avm-motion produced no samples")
        last = samples[-1]
        path = [(s["x"], s["y"]) for s in samples]
        return MotionResult(
            samples=samples,
            final_error=float((last["ex"] ** 2 + last["ey"] ** 2) ** 0.5),
            path=path,
        )
