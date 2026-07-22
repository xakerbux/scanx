"""Эвристики: огонь, дым, вода."""

from __future__ import annotations

import cv2
import numpy as np

from cv_module.inference.base import Detection


class HeuristicDetector:
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> list[Detection]:
        out: list[Detection] = []
        out.extend(self._fire_smoke(frame))
        out.extend(self._water(frame))
        return [d for d in out if d.confidence >= self.confidence]

    def _fire_smoke(self, frame: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        dets: list[Detection] = []
        for mask, cls, evt, sev in (
            (cv2.inRange(hsv, (5, 120, 120), (35, 255, 255)), "fire", "fire_detected", "critical"),
            (cv2.inRange(hsv, (0, 0, 80), (180, 60, 220)), "smoke", "smoke_detected", "high"),
        ):
            for c in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                if cv2.contourArea(c) < frame.shape[0] * frame.shape[1] * 0.002:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                conf = min(0.99, 0.5 + cv2.contourArea(c) / (frame.shape[0] * frame.shape[1]))
                dets.append(Detection(cls, evt, conf, {"x": x, "y": y, "width": w, "height": h}, sev, "heuristic"))
        return dets

    def _water(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        roi = frame[int(h * 0.4):]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (85, 40, 40), (130, 255, 255))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        dets: list[Detection] = []
        for c in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            if cv2.contourArea(c) < roi.shape[0] * roi.shape[1] * 0.008:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            conf = min(0.95, 0.45 + cv2.contourArea(c) / (roi.shape[0] * roi.shape[1]))
            dets.append(
                Detection(
                    "water",
                    "water_detected",
                    conf,
                    {"x": x, "y": y + int(h * 0.4), "width": bw, "height": bh},
                    "high",
                    "heuristic_water",
                )
            )
        return dets
