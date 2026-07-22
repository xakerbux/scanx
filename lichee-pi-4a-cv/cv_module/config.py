"""Конфигурация приложения."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class AppConfig:
    mode: str = "demo"
    input_source: str = "file"  # file | builtin | external
    camera_role: str = "builtin"  # legacy, см. normalize_input()
    camera_id: int = 0
    camera_width: int = 640
    camera_height: int = 480
    video_path: str = ""
    videos_dir: str = "videos"
    model_path: str = "models/yolov8n.onnx"
    confidence_threshold: float = 0.45
    input_size: tuple[int, int] = (640, 640)
    frame_skip: int = 0
    loop_video: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8080
    save_event_frames: bool = False
    max_events: int = 300
    event_frame_quality: int = 65
    event_frame_max_width: int = 320
    events_dir: str = "data/events"
    events_db_path: str = "data/events.json"
    logs_dir: str = "data/logs"
    camera_id_label: str = "cam_01"
    use_onnx: bool = True
    mock_inference: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        size = raw.get("input_size", [640, 640])
        if isinstance(size, list):
            raw = {**raw, "input_size": (int(size[0]), int(size[1]))}
        known = {f.name for f in cls.__dataclass_fields__.values()}
        cfg = cls(**{k: v for k, v in raw.items() if k in known}).resolve_paths()
        cfg.normalize_input()
        return cfg

    def resolve_paths(self) -> "AppConfig":
        for attr in ("video_path", "videos_dir", "model_path", "events_dir", "events_db_path", "logs_dir"):
            value = getattr(self, attr)
            path = Path(value)
            if not path.is_absolute():
                setattr(self, attr, str((PROJECT_ROOT / path).resolve()))
        return self

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["input_size"] = list(self.input_size)
        return data

    def apply_updates(self, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            if not hasattr(self, key):
                continue
            if key == "input_size" and isinstance(value, list):
                value = (int(value[0]), int(value[1]))
            setattr(self, key, value)
        self.resolve_paths()
        self.normalize_input()

    def normalize_input(self) -> None:
        if self.input_source == "camera":
            self.input_source = "external" if self.camera_role == "external" else "builtin"
        elif self.input_source == "browser":
            self.input_source = "builtin"

    def resolved_input_source(self) -> str:
        self.normalize_input()
        if self.input_source in ("file", "builtin", "external"):
            return self.input_source
        return "file"

    def resolved_camera_id(self) -> int:
        source = self.resolved_input_source()
        if source in ("builtin", "external"):
            if self.camera_id >= 0:
                return self.camera_id
            return 1 if source == "external" else 0
        return self.camera_id


def load_config(config_path: str | None = None) -> AppConfig:
    path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "default.yaml"
    if path.exists():
        cfg = AppConfig.from_yaml(path)
    else:
        cfg = AppConfig().resolve_paths()
    cfg.normalize_input()
    return cfg


def detect_platform_mode() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else ""
    return "edge" if "riscv" in machine.lower() else "demo"
