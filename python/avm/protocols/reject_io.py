from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RejectEvent:
    sample_id: str
    ok: bool
    label: str
    confidence: float
    coil: str
    timestamp: str
    note: str


class VirtualRejectIO:
    """Stand-in for Modbus/PLC reject coil until real industrial I/O is attached."""

    def __init__(self, log_path: Path, coil: str = "Q0.1"):
        self.log_path = Path(log_path)
        self.coil = coil
        self.events: list[RejectEvent] = []
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, sample_id: str, ok: bool, label: str, confidence: float, note: str = "") -> RejectEvent:
        event = RejectEvent(
            sample_id=sample_id,
            ok=ok,
            label=label,
            confidence=confidence,
            coil=self.coil if not ok else "",
            timestamp=datetime.now(timezone.utc).isoformat(),
            note=note if note else ("PASS" if ok else f"REJECT {label}"),
        )
        self.events.append(event)
        return event

    def dump(self) -> Path:
        payload = [asdict(e) for e in self.events]
        self.log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.log_path
