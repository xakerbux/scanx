"""Проверка камеры после восстановления."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cv_module.input.camera_source import CameraSource  # noqa: E402


def main() -> int:
    cams = CameraSource.probe()
    print("probe", cams)
    src = CameraSource(0)
    opened = src.open()
    print("open", opened, src.last_error)
    if opened:
        ok, frame = src.read()
        print("read", ok, frame.shape if ok and frame is not None else None)
        src.close()
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
