#!/usr/bin/env python3
"""Скачивание YOLOv8n ONNX."""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models" / "yolov8n.onnx"
URLS = [
    "https://huggingface.co/Kalray/yolov8/resolve/main/yolov8n.onnx",
    "https://huggingface.co/cabelo/yolov8/resolve/main/yolov8n.onnx",
]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and OUT.stat().st_size > 5_000_000:
        print(f"OK: {OUT}")
        return 0
    for url in URLS:
        print(f"Download {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cv-module/2"})
            data = urllib.request.urlopen(req, timeout=120).read()
            if len(data) > 5_000_000:
                OUT.write_bytes(data)
                print(f"Saved: {OUT}")
                return 0
        except Exception as e:
            print(e)
    print("Failed. Run: python main.py --mock", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
