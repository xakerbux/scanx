"""Гибридный детектор: люди, транспорт, огонь, дым, вода, без каски."""

from __future__ import annotations

import numpy as np

from cv_module.inference.base import Detection
from cv_module.inference.classes import ALLOWED_CLASSES
from cv_module.inference.helmet import HelmetDetector
from cv_module.inference.heuristics import HeuristicDetector
from cv_module.inference.yolo_onnx import YoloOnnxDetector


class HybridDetector:
    CLASS_INFO = {
        "person": {"real": True, "method": "YOLOv8n ONNX"},
        "vehicle": {"real": True, "method": "YOLOv8n ONNX"},
        "fire": {"real": False, "method": "HSV-эвристика"},
        "smoke": {"real": False, "method": "HSV-эвристика"},
        "water": {"real": False, "method": "HSV-эвристика воды"},
        "no_helmet": {"real": False, "method": "HSV-эвристика каски (область головы)"},
    }

    def __init__(self, model_path: str, confidence: float, input_size: tuple[int, int], use_onnx=True, mock=False) -> None:
        self.confidence = confidence
        self.mock = mock
        self.yolo = YoloOnnxDetector(model_path, confidence, input_size) if use_onnx else None
        self.heuristics = HeuristicDetector(confidence)
        self.helmet = HelmetDetector(confidence)

    @property
    def runtime_info(self) -> dict:
        ok = self.yolo and self.yolo.available
        return {
            "runtime": "onnxruntime" if ok else "opencv_heuristics",
            "model_format": "ONNX YOLOv8n" if ok else "none",
            "model_path": self.yolo.model_path if self.yolo else None,
            "classes": self.CLASS_INFO,
            "allowed_classes": sorted(ALLOWED_CLASSES),
        }

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        if self.mock:
            h, w = frame_bgr.shape[:2]
            return [
                Detection("person", "person_detected", 0.9, {"x": w // 3, "y": h // 4, "width": 100, "height": 200}, "medium", "mock"),
                Detection("vehicle", "vehicle_detected", 0.85, {"x": w // 2, "y": h // 2, "width": 180, "height": 90}, "medium", "mock"),
                Detection("fire", "fire_detected", 0.8, {"x": w // 2, "y": h // 6, "width": 60, "height": 60}, "critical", "mock"),
                Detection("no_helmet", "no_helmet_detected", 0.88, {"x": w // 3, "y": h // 4, "width": 100, "height": 200}, "high", "mock"),
            ]
        yolo_dets: list[Detection] = []
        if self.yolo and self.yolo.available:
            yolo_dets = [d for d in self.yolo.detect(frame_bgr) if d and d.object_class in ALLOWED_CLASSES]
        persons = [d for d in yolo_dets if d.object_class == "person"]
        helmet_dets = self.helmet.detect(frame_bgr, persons)
        all_dets = yolo_dets + helmet_dets + self.heuristics.detect(frame_bgr)
        filtered = [d for d in self._dedupe(all_dets) if d.object_class in ALLOWED_CLASSES and d.confidence >= self.confidence]
        return filtered

    @staticmethod
    def _dedupe(dets: list[Detection]) -> list[Detection]:
        best: dict[tuple, Detection] = {}
        for d in dets:
            key = (d.object_class, d.bbox["x"] // 20, d.bbox["y"] // 20)
            if key not in best or d.confidence > best[key].confidence:
                best[key] = d
        return list(best.values())
