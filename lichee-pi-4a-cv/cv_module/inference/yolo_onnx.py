"""YOLOv8n ONNX."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from cv_module.inference.base import Detection

logger = logging.getLogger("cv_module.inference.yolo")

COCO = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
]
VEHICLES = {"car", "truck", "bus", "motorcycle", "bicycle", "train", "boat"}


class YoloOnnxDetector:
    def __init__(self, model_path: str, confidence: float, input_size: tuple[int, int]) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.input_size = input_size
        self.session = None
        self.input_name = ""
        self.available = False
        self._load()

    def _load(self) -> None:
        if not Path(self.model_path).exists():
            logger.warning("ONNX модель не найдена: %s", self.model_path)
            return
        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name
            self.available = True
            logger.info("YOLO ONNX загружена: %s", self.model_path)
        except Exception as exc:
            logger.error("Ошибка загрузки ONNX: %s", exc)

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        if not self.available or self.session is None:
            return []
        h, w = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(frame_bgr, 1 / 255.0, self.input_size, swapRB=True, crop=False)
        out = self.session.run(None, {self.input_name: blob})[0]
        preds = out[0].T if out.ndim == 3 else out.T
        boxes: list[tuple[int, int, int, int, float, int]] = []
        for row in preds:
            if row.shape[0] < 5:
                continue
            scores = row[4:]
            cid = int(np.argmax(scores))
            score = float(scores[cid])
            if score < self.confidence:
                continue
            cx, cy, bw, bh = row[:4]
            x1 = int((cx - bw / 2) * w / self.input_size[0])
            y1 = int((cy - bh / 2) * h / self.input_size[1])
            x2 = int((cx + bw / 2) * w / self.input_size[0])
            y2 = int((cy + bh / 2) * h / self.input_size[1])
            boxes.append((x1, y1, x2, y2, score, cid))
        kept = self._nms(boxes)
        dets: list[Detection] = []
        for x1, y1, x2, y2, score, cid in kept:
            if cid >= len(COCO):
                continue
            det = self._to_det(x1, y1, x2, y2, score, cid)
            if det:
                dets.append(det)
        return dets

    def _to_det(self, x1, y1, x2, y2, score, cid) -> Detection | None:
        name = COCO[cid]
        if name == "person":
            return Detection("person", "person_detected", score, {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}, "medium", "yolo_onnx")
        if name in VEHICLES:
            return Detection("vehicle", "vehicle_detected", score, {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}, "medium", "yolo_onnx")
        return None

    def _nms(self, boxes, iou=0.45):
        if not boxes:
            return []
        boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
        kept = []
        while boxes:
            best = boxes.pop(0)
            kept.append(best)
            boxes = [b for b in boxes if self._iou(best, b) < iou]
        return kept

    @staticmethod
    def _iou(a, b):
        ax1, ay1, ax2, ay2 = a[:4]
        bx1, by1, bx2, by2 = b[:4]
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = max(0, ax2 - ax1) * max(0, ay2 - ay1) + max(0, bx2 - bx1) * max(0, by2 - by1) - inter
        return inter / union if union else 0.0
