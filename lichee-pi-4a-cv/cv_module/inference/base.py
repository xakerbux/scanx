from dataclasses import dataclass


@dataclass
class Detection:
    object_class: str
    event_type: str
    confidence: float
    bbox: dict[str, int]
    severity: str = "medium"
    source: str = "model"

    def to_dict(self) -> dict:
        return {
            "object_class": self.object_class,
            "event_type": self.event_type,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox,
            "severity": self.severity,
            "source": self.source,
        }
