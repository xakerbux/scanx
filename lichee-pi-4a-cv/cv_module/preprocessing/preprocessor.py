"""Предобработка кадров."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    original: np.ndarray
    resized: np.ndarray
    scale_x: float
    scale_y: float


class FramePreprocessor:
    def __init__(self, input_size: tuple[int, int], frame_skip: int = 0) -> None:
        self.input_size = input_size
        self.frame_skip = max(0, frame_skip)
        self._index = 0

    def process(self, frame: np.ndarray) -> PreprocessResult | None:
        self._index += 1
        if self.frame_skip > 0 and self._index % (self.frame_skip + 1) != 0:
            return None

        h, w = frame.shape[:2]
        tw, th = self.input_size
        resized = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        return PreprocessResult(frame, rgb, w / tw, h / th)
