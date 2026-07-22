"""Эвристика: человек без каски (по области головы в bbox person)."""

from __future__ import annotations

import cv2
import numpy as np

from cv_module.inference.base import Detection


class HelmetDetector:
    """Проверяет наличие каски в верхней части bbox человека."""

    HELMET_MIN_RATIO = 0.07

    def __init__(self, confidence: float) -> None:
        self.confidence = confidence

    def detect(self, frame: np.ndarray, persons: list[Detection]) -> list[Detection]:
        out: list[Detection] = []
        fh, fw = frame.shape[:2]
        for person in persons:
            det = self._check_person(frame, person, fh, fw)
            if det and det.confidence >= self.confidence:
                out.append(det)
        return out

    def _check_person(self, frame: np.ndarray, person: Detection, fh: int, fw: int) -> Detection | None:
        x, y, w, h = person.bbox["x"], person.bbox["y"], person.bbox["width"], person.bbox["height"]
        if w < 20 or h < 40:
            return None

        head_h = max(10, int(h * 0.22))
        head_w = max(10, int(w * 0.72))
        head_x = x + (w - head_w) // 2
        head_y = y

        x1 = max(0, head_x)
        y1 = max(0, head_y)
        x2 = min(fw, head_x + head_w)
        y2 = min(fh, head_y + head_h)
        if x2 <= x1 or y2 <= y1:
            return None

        roi = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        helmet_mask = (
            cv2.inRange(hsv, (15, 70, 70), (35, 255, 255))  # жёлтые
            | cv2.inRange(hsv, (5, 90, 90), (14, 255, 255))  # оранжевые
            | cv2.inRange(hsv, (0, 0, 170), (180, 45, 255))  # белые/светлые
            | cv2.inRange(hsv, (95, 45, 45), (125, 255, 255))  # синие
            | cv2.inRange(hsv, (0, 90, 90), (4, 255, 255))  # красные
        )
        helmet_ratio = float(np.count_nonzero(helmet_mask)) / helmet_mask.size
        if helmet_ratio >= self.HELMET_MIN_RATIO:
            return None

        conf = min(0.95, 0.52 + (1.0 - helmet_ratio) * 0.35)
        return Detection(
            "no_helmet",
            "no_helmet_detected",
            conf,
            {"x": x, "y": y, "width": w, "height": h},
            "high",
            "heuristic_helmet",
        )
