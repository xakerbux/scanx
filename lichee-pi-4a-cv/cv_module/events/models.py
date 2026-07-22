from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Event:
    id: str
    timestamp: str
    event_type: str
    object_class: str
    confidence: float
    bbox: dict[str, int]
    frame_path: str | None = None
    camera_id: str = "cam_01"
    severity: str = "medium"
    status: str = "new"
    source: str = "model"
    extra: dict[str, Any] = field(default_factory=dict)
    fps: float = 0.0
    detection_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
