"""Хранилище событий."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import cv2
import numpy as np

from cv_module.events.models import Event, utc_now_iso
from cv_module.inference.base import Detection

logger = logging.getLogger("cv_module.events")


class EventStore:
    def __init__(
        self,
        db_path: str,
        events_dir: str,
        save_frames: bool = False,
        max_events: int = 300,
        frame_quality: int = 65,
        frame_max_width: int = 320,
        project_root: Path | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.events_dir = Path(events_dir)
        self.save_frames = save_frames
        self.max_events = max(1, max_events)
        self.frame_quality = max(30, min(frame_quality, 95))
        self.frame_max_width = max(80, frame_max_width)
        self._project_root = project_root or self.db_path.parent.parent
        self._lock = threading.Lock()
        self._events: list[Event] = []
        self._counter = 0
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.db_path.exists():
            return
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            self._events = [Event(**e) for e in data.get("events", [])]
            self._counter = int(data.get("counter", len(self._events)))
            self._trim(rewrite=False)
        except Exception as exc:
            logger.error("Ошибка загрузки событий: %s", exc)

    def _save(self) -> None:
        payload = {"counter": self._counter, "events": [e.to_dict() for e in self._events]}
        self.db_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    def _rel_path(self, path: str) -> str:
        try:
            return str(Path(path).relative_to(self._project_root))
        except ValueError:
            return path

    def _frame_file(self, frame_path: str | None) -> Path | None:
        if not frame_path:
            return None
        path = Path(frame_path)
        if not path.is_absolute():
            path = self._project_root / path
        return path

    def _save_frame(self, eid: str, frame: np.ndarray, bbox: dict[str, int]) -> str | None:
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        fh, fw = frame.shape[:2]
        pad = 8
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(fw, x + w + pad), min(fh, y + h + pad)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        max_w = self.frame_max_width
        if crop.shape[1] > max_w:
            scale = max_w / crop.shape[1]
            crop = cv2.resize(crop, (max_w, max(1, int(crop.shape[0] * scale))))

        rel = self.events_dir / f"{eid}.jpg"
        cv2.imwrite(
            str(rel),
            crop,
            [cv2.IMWRITE_JPEG_QUALITY, self.frame_quality],
        )
        return self._rel_path(str(rel))

    def _trim(self, *, rewrite: bool = True) -> None:
        changed = False
        while len(self._events) > self.max_events:
            old = self._events.pop(0)
            frame_file = self._frame_file(old.frame_path)
            if frame_file and frame_file.exists():
                try:
                    frame_file.unlink()
                except OSError as exc:
                    logger.warning("Не удалось удалить %s: %s", frame_file, exc)
            changed = True
        if changed and rewrite:
            self._save()

    def create(
        self,
        det: Detection,
        frame: np.ndarray | None,
        camera_id: str,
        *,
        fps: float = 0.0,
        detection_ms: float = 0.0,
    ) -> Event | None:
        with self._lock:
            for e in reversed(self._events[-20:]):
                if e.object_class == det.object_class and self._same(e.bbox, det.bbox):
                    return None
            self._counter += 1
            eid = f"evt_{self._counter:06d}"
            fpath = None
            if self.save_frames and frame is not None:
                fpath = self._save_frame(eid, frame, det.bbox)
            event = Event(
                eid,
                utc_now_iso(),
                det.event_type,
                det.object_class,
                det.confidence,
                det.bbox,
                fpath,
                camera_id,
                det.severity,
                "new",
                det.source,
                fps=round(fps, 2),
                detection_ms=round(detection_ms, 1),
            )
            self._events.append(event)
            self._trim(rewrite=False)
            self._save()
            logger.info("Событие %s: %s (%.2f)", eid, det.object_class, det.confidence)
            return event

    def list_events(self, limit=100) -> list[Event]:
        with self._lock:
            return list(reversed(self._events[-limit:]))

    def get(self, event_id: str) -> Event | None:
        with self._lock:
            return next((e for e in self._events if e.id == event_id), None)

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    @staticmethod
    def _same(a, b, tol=30) -> bool:
        return all(abs(a[k] - b[k]) < tol for k in ("x", "y", "width", "height"))
