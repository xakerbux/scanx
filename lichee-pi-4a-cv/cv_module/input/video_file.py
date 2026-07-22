"""Работа с локальным хранилищем видеофайлов."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2

logger = logging.getLogger("cv_module.input")

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"}


def list_local_videos(videos_dir: str) -> list[dict[str, str]]:
    root = Path(videos_dir)
    root.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            files.append(
                {
                    "name": path.name,
                    "path": str(path.resolve()),
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                }
            )
    return files


class VideoFileSource:
    """Чтение кадров из локального видеофайла."""

    def __init__(self, video_path: str, loop: bool = True) -> None:
        self.video_path = str(Path(video_path).resolve())
        self.loop = loop
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
        path = Path(self.video_path)
        if not path.exists():
            self._last_error = f"Видеофайл не найден: {self.video_path}"
            logger.error(self._last_error)
            return False
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            self._last_error = f"Неподдерживаемый формат: {path.suffix}"
            logger.error(self._last_error)
            return False

        self._capture = cv2.VideoCapture(self.video_path)
        if not self._capture.isOpened():
            self._last_error = f"Не удалось открыть видео: {self.video_path}"
            logger.error(self._last_error)
            return False

        self._opened = True
        self._last_error = None
        logger.info("Открыт видеофайл: %s", self.video_path)
        return True

    def read(self) -> tuple[bool, object | None]:
        if not self.is_open or self._capture is None:
            self._last_error = "Видеофайл не открыт"
            return False, None

        ok, frame = self._capture.read()
        if ok and frame is not None:
            return True, frame

        if self.loop:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._capture.read()
            if ok and frame is not None:
                return True, frame

        self._last_error = "Ошибка чтения кадра"
        return False, None

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self._opened = False

    def describe(self) -> str:
        return self.video_path
