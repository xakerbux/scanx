"""Конвейер обработки: видеофайл или камера."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import cv2
import numpy as np

from cv_module.config import AppConfig
from cv_module.events.store import EventStore
from cv_module.inference.classes import CLASS_COLORS, CLASS_LABELS
from cv_module.inference.detector import HybridDetector
from cv_module.input.camera_source import CameraSource
from cv_module.input.video_file import VideoFileSource
from cv_module.preprocessing.preprocessor import FramePreprocessor

logger = logging.getLogger("cv_module.pipeline")


class State(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class Metrics:
    fps: float = 0.0
    latency_ms: float = 0.0
    frames_processed: int = 0
    last_detections: list[dict] = field(default_factory=list)


class VideoPipeline:
    def __init__(self, config: AppConfig, store: EventStore) -> None:
        self.config = config
        self.store = store
        self.state = State.STOPPED
        self.error: str | None = None
        self.metrics = Metrics()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._lat = deque(maxlen=30)
        self._fps = deque(maxlen=30)
        self._pause_keep_source = False
        self.detector = HybridDetector(
            config.model_path,
            config.confidence_threshold,
            config.input_size,
            config.use_onnx,
            config.mock_inference,
        )
        self.preprocessor = FramePreprocessor(config.input_size, config.frame_skip)
        self.source: VideoFileSource | CameraSource | None = None
        self._build_source()

    def _build_source(self) -> None:
        source = self.config.resolved_input_source()
        if source in ("builtin", "external"):
            cam_id = self.config.resolved_camera_id()
            self.source = CameraSource(cam_id, self.config.camera_width, self.config.camera_height)
        elif source == "file" and self.config.video_path:
            self.source = VideoFileSource(self.config.video_path, self.config.loop_video)
        else:
            self.source = None

    def start(self) -> bool:
        if self.state == State.RUNNING:
            return True
        self._stop.clear()
        self.error = None

        if self.state == State.PAUSED:
            if self.source is None:
                self.state = State.ERROR
                self.error = "Источник не настроен"
                return False
            if not self.source.is_open and not self.source.open():
                self.state = State.ERROR
                self.error = self.source.last_error
                return False
            self.state = State.RUNNING
            self._thread = threading.Thread(target=self._loop, daemon=True, name="cv-pipeline")
            self._thread.start()
            logger.info("Обработка возобновлена: %s", self.source.describe())
            return True

        if self.source is None:
            self.state = State.ERROR
            self.error = "Источник не настроен"
            return False
        if not self.source.open():
            self.state = State.ERROR
            self.error = self.source.last_error
            return False

        self.state = State.RUNNING
        self._thread = threading.Thread(target=self._loop, daemon=True, name="cv-pipeline")
        self._thread.start()
        logger.info("Обработка запущена: %s", self.source.describe())
        return True

    def pause(self) -> None:
        if self.state != State.RUNNING:
            return
        self._pause_keep_source = True
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        self.state = State.PAUSED
        logger.info("Обработка на паузе")

    def stop(self) -> None:
        self._pause_keep_source = False
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        if self.source:
            self.source.close()
        self.state = State.STOPPED

    def update_config(self, config: AppConfig) -> None:
        prev_path = self.config.video_path if self.config.resolved_input_source() == "file" else None
        config.normalize_input()
        self.config = config
        self.detector.confidence = config.confidence_threshold
        if self.detector.yolo:
            self.detector.yolo.confidence = config.confidence_threshold
        self.preprocessor = FramePreprocessor(config.input_size, config.frame_skip)
        if self.state == State.PAUSED and config.resolved_input_source() == "file" and config.video_path == prev_path:
            return
        self._build_source()

    def get_frame_jpeg(self) -> bytes | None:
        with self._lock:
            if self._frame is None:
                return None
            ok, buf = cv2.imencode(".jpg", self._frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            return buf.tobytes() if ok else None

    def status(self) -> dict[str, Any]:
        source = self.config.resolved_input_source()
        return {
            "state": self.state.value,
            "input_source": source,
            "camera_id": self.config.resolved_camera_id() if source in ("builtin", "external") else None,
            "video_path": self.config.video_path,
            "video_source": self.source.describe() if self.source else "",
            "fps": round(self.metrics.fps, 2),
            "latency_ms": round(self.metrics.latency_ms, 2),
            "frames_processed": self.metrics.frames_processed,
            "events_total": self.store.count(),
            "confidence_threshold": self.config.confidence_threshold,
            "error": self.error,
            "detections": self.metrics.last_detections,
            "runtime": self.detector.runtime_info,
        }

    def _loop(self) -> None:
        read_errors = 0
        while not self._stop.is_set():
            if self.source is None:
                break
            t0 = time.perf_counter()
            ok, frame = self.source.read()
            if not ok or frame is None:
                read_errors += 1
                if read_errors < 30:
                    time.sleep(0.1)
                    continue
                self.state = State.ERROR
                self.error = self.source.last_error or "Ошибка чтения"
                break
            read_errors = 0
            self._process(frame, t0)
        if self.source and not self._pause_keep_source:
            self.source.close()

    def _process(self, frame: np.ndarray, t0: float) -> None:
        prep = self.preprocessor.process(frame)
        dets = []
        if prep is not None:
            t1 = time.perf_counter()
            dets = self.detector.detect(prep.original)
            self._lat.append((time.perf_counter() - t1) * 1000)
            self.metrics.latency_ms = sum(self._lat) / len(self._lat)
        annotated = self._draw(frame, dets)
        with self._lock:
            self._frame = annotated
        for d in dets:
            self.store.create(
                d,
                annotated,
                self.config.camera_id_label,
                fps=self.metrics.fps,
                detection_ms=self.metrics.latency_ms,
            )
        elapsed = time.perf_counter() - t0
        if elapsed > 0:
            self._fps.append(1 / elapsed)
            self.metrics.fps = sum(self._fps) / len(self._fps)
        self.metrics.frames_processed += 1
        self.metrics.last_detections = [d.to_dict() for d in dets]

    def _draw(self, frame, dets) -> np.ndarray:
        out = frame.copy()
        for d in dets:
            c = CLASS_COLORS.get(d.object_class, (255, 255, 255))
            x, y, w, h = d.bbox["x"], d.bbox["y"], d.bbox["width"], d.bbox["height"]
            cv2.rectangle(out, (x, y), (x + w, y + h), c, 2)
            label = CLASS_LABELS.get(d.object_class, d.object_class)
            cv2.putText(out, label, (x, max(22, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
        return out
