"""Восстановление доступа к камере без прав администратора."""

from __future__ import annotations

import logging
import platform
import subprocess
import time
from pathlib import Path

from cv_module.input.camera_source import CameraSource

logger = logging.getLogger("cv_module.camera_fix")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "scripts" / "fix_camera.log"


def _log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    logger.info(msg)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _run(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip()
    except Exception as exc:
        return str(exc)


def _stop_conflicts() -> None:
    if platform.system() != "Windows":
        return
    for name in ("droidcam",):
        out = _run(["taskkill", "/IM", f"{name}.exe", "/F"])
        if out:
            _log(f"taskkill {name}: {out[:200]}")


def fix_camera() -> dict:
    """Освободить камеру, переустановить usbvideo, просканировать устройства."""
    _log("=== fix_camera start ===")
    _stop_conflicts()

    if platform.system() == "Windows":
        _log(_run(["pnputil", "/add-driver", r"C:\Windows\INF\usbvideo.inf", "/install"])[:500])
        _run([
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PnpDevice -Class Camera -EA SilentlyContinue | "
            "Where-Object { $_.Status -ne 'OK' } | "
            "ForEach-Object { Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -EA SilentlyContinue }",
        ])
        _log(_run(["pnputil", "/scan-devices"])[:300])
        _run([
            "powershell",
            "-NoProfile",
            "-Command",
            "Restart-Service FrameServer -Force -EA SilentlyContinue",
        ])

    time.sleep(1.5)
    cameras = CameraSource.probe()
    _log(f"working={cameras}")
    _log("=== fix_camera done ===")
    return {
        "ok": bool(cameras),
        "cameras": cameras,
        "log_path": str(LOG_PATH),
    }
