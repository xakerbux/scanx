"""Полный проход по видеофайлу с экспортом детекций в JSON."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

import cv2

from cv_module.config import AppConfig
from cv_module.events.models import utc_now_iso
from cv_module.inference.classes import CLASS_LABELS
from cv_module.inference.detector import HybridDetector
from cv_module.preprocessing.preprocessor import FramePreprocessor

logger = logging.getLogger("cv_module.render")


def _format_time(sec: float) -> str:
    minutes = int(sec // 60)
    seconds = sec % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def render_video(
    config: AppConfig,
    video_path: str,
    confidence_threshold: float | None = None,
) -> dict:
    path = Path(video_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Видеофайл не найден: {video_path}")

    threshold = confidence_threshold if confidence_threshold is not None else config.confidence_threshold
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_sec = total_frames / fps if fps > 0 and total_frames > 0 else 0.0

    detector = HybridDetector(
        config.model_path,
        threshold,
        config.input_size,
        config.use_onnx,
        config.mock_inference,
    )
    preprocessor = FramePreprocessor(config.input_size, config.frame_skip)

    detections: list[dict] = []
    frame_idx = 0
    processed = 0

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        time_sec = frame_idx / fps if fps > 0 else 0.0
        prep = preprocessor.process(frame)
        if prep is not None:
            processed += 1
            for det in detector.detect(prep.original):
                detections.append(
                    {
                        "frame": frame_idx,
                        "time_sec": round(time_sec, 3),
                        "time_code": _format_time(time_sec),
                        "object_class": det.object_class,
                        "object_label": CLASS_LABELS.get(det.object_class, det.object_class),
                        "confidence": round(det.confidence, 4),
                        "confidence_pct": round(det.confidence * 100, 1),
                        "bbox": det.bbox,
                        "source": det.source,
                    }
                )
        frame_idx += 1

    cap.release()

    by_class = Counter(d["object_class"] for d in detections)
    report = {
        "schema": "cv-module-render/v1",
        "rendered_at": utc_now_iso(),
        "video_path": str(path),
        "video_name": path.name,
        "video": {
            "fps": round(fps, 3),
            "frame_count": frame_idx,
            "processed_frames": processed,
            "width": width,
            "height": height,
            "duration_sec": round(duration_sec, 3),
        },
        "confidence_threshold": threshold,
        "detections": detections,
        "summary": {
            "total_detections": len(detections),
            "by_class": dict(sorted(by_class.items())),
            "by_label": {
                CLASS_LABELS.get(k, k): v for k, v in sorted(by_class.items())
            },
        },
    }
    logger.info("Render %s: %s frames, %s detections", path.name, frame_idx, len(detections))
    return report
