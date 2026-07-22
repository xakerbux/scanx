"""Настройка логирования."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(logs_dir: str) -> logging.Logger:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("cv_module")
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    file_handler = RotatingFileHandler(
        Path(logs_dir) / "cv_module.log",
        maxBytes=512 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(stream)
    root.addHandler(file_handler)
    return root
