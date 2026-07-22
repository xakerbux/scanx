"""Источник камеры через OpenCV."""

from __future__ import annotations

import logging
import platform
import time

import cv2

logger = logging.getLogger("cv_module.input.camera")


def _backend_order() -> list[int | None]:
    system = platform.system()
    if system == "Windows":
        order: list[int | None] = []
        dshow = getattr(cv2, "CAP_DSHOW", None)
        msf = getattr(cv2, "CAP_MSMF", None)
        if dshow is not None:
            order.append(dshow)
        if msf is not None:
            order.append(msf)
        order.append(None)
        return order
    if system == "Linux":
        v4l = getattr(cv2, "CAP_V4L2", None)
        return [v4l, None] if v4l is not None else [None]
    return [None]


def _warmup(cap: cv2.VideoCapture, attempts: int = 5) -> bool:
    for _ in range(attempts):
        ok, frame = cap.read()
        if ok and frame is not None:
            return True
        time.sleep(0.05)
    return False


def _try_open(index: int) -> cv2.VideoCapture | None:
    for backend in _backend_order():
        try:
            cap = cv2.VideoCapture(index, backend) if backend is not None else cv2.VideoCapture(index)
        except Exception as exc:
            logger.debug("VideoCapture(%s, %s) failed: %s", index, backend, exc)
            continue
        if not cap.isOpened():
            cap.release()
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if _warmup(cap, attempts=5):
            return cap
        cap.release()
    return None


class CameraSource:
    def __init__(self, camera_id: int, width: int = 640, height: int = 480) -> None:
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self._capture: cv2.VideoCapture | None = None
        self._opened = False
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def is_open(self) -> bool:
        return self._opened and self._capture is not None and self._capture.isOpened()

    def open(self) -> bool:
        self.close()
        cap = _try_open(self.camera_id)
        if cap is None:
            self._last_error = f"Не удалось открыть камеру #{self.camera_id}"
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._capture = cap
        self._opened = True
        self._last_error = None
        logger.info("Камера #%s открыта", self.camera_id)
        return True

    def read(self):
        if not self.is_open or self._capture is None:
            self._last_error = "Камера не открыта"
            return False, None

        for _ in range(3):
            ok, frame = self._capture.read()
            if ok and frame is not None:
                return True, frame
            time.sleep(0.03)

        self._last_error = "Ошибка чтения кадра с камеры"
        return False, None

    def close(self) -> None:
        if self._capture:
            self._capture.release()
        self._capture = None
        self._opened = False

    def describe(self) -> str:
        return f"camera:{self.camera_id}"

    @staticmethod
    def probe(max_index: int = 3) -> list[dict]:
        """Проверка камер. Вызывать только по запросу, не при каждом клике в UI."""
        found: list[dict] = []
        for index in range(max_index + 1):
            cap = _try_open(index)
            if cap is None:
                continue
            cap.release()
            found.append({
                "id": index,
                "label": f"Камера {index}",
            })
        return found
