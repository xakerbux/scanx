"""FastAPI REST API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cv_module.config import AppConfig, PROJECT_ROOT
from cv_module.events.store import EventStore
from cv_module.input.camera_source import CameraSource
from cv_module.input.video_file import list_local_videos
from cv_module.pipeline.processor import VideoPipeline
from cv_module.pipeline.render import render_video

UI = PROJECT_ROOT / "cv_module" / "ui" / "static"


class ConfigUpdate(BaseModel):
    input_source: str | None = None
    camera_role: str | None = None  # legacy
    camera_id: int | None = None
    video_path: str | None = None
    confidence_threshold: float | None = Field(default=None, ge=0.05, le=0.99)
    frame_skip: int | None = Field(default=None, ge=0, le=10)


class RenderRequest(BaseModel):
    video_path: str | None = None
    confidence_threshold: float | None = Field(default=None, ge=0.05, le=0.99)


def create_app(config: AppConfig) -> FastAPI:
    config.normalize_input()
    store = EventStore(
        config.events_db_path,
        config.events_dir,
        save_frames=config.save_event_frames,
        max_events=config.max_events,
        frame_quality=config.event_frame_quality,
        frame_max_width=config.event_frame_max_width,
        project_root=PROJECT_ROOT,
    )
    pipeline = VideoPipeline(config, store)

    app = FastAPI(title="CV Module SATK", version="2.2.0")
    app.state.config = config
    app.state.pipeline = pipeline

    if UI.exists():
        app.mount("/static", StaticFiles(directory=str(UI)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(UI / "index.html")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/status")
    async def status() -> dict:
        return pipeline.status()

    @app.get("/videos")
    async def videos() -> dict:
        items = list_local_videos(config.videos_dir)
        return {"videos": items}

    @app.get("/cameras")
    async def cameras() -> dict:
        return {"cameras": CameraSource.probe()}

    @app.get("/events")
    async def events(limit: int = 100) -> dict:
        return {"events": [e.to_dict() for e in store.list_events(limit)]}

    @app.get("/events/{event_id}")
    async def event(event_id: str) -> dict:
        item = store.get(event_id)
        if not item:
            raise HTTPException(404, "Not found")
        return item.to_dict()

    @app.post("/start")
    async def start() -> dict:
        config.normalize_input()
        pipeline.update_config(config)
        if not pipeline.start():
            raise HTTPException(400, pipeline.error or "Start failed")
        return {"status": "running"}

    @app.post("/stop")
    async def stop() -> dict:
        pipeline.stop()
        return {"status": "stopped"}

    @app.post("/pause")
    async def pause() -> dict:
        pipeline.pause()
        return {"status": pipeline.state.value}

    @app.post("/render")
    async def render(body: RenderRequest) -> dict:
        """Полный проход по видео: все детекции от начала до конца."""
        video_path = body.video_path or config.video_path
        if not video_path:
            raise HTTPException(400, "Не указан видеофайл")
        if pipeline.state.value in ("running", "paused"):
            pipeline.stop()
        try:
            return render_video(config, video_path, body.confidence_threshold)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/config")
    async def set_config(body: ConfigUpdate) -> dict:
        config.apply_updates(body.model_dump(exclude_none=True))
        pipeline.update_config(config)
        return {"status": "updated", "config": config.to_dict()}

    @app.get("/frame/latest")
    async def frame() -> Response:
        data = pipeline.get_frame_jpeg()
        if not data:
            raise HTTPException(404, "No frame")
        return Response(data, media_type="image/jpeg")

    @app.get("/metrics")
    async def metrics() -> dict:
        s = pipeline.status()
        return {k: s[k] for k in ("fps", "latency_ms", "frames_processed", "events_total", "state")}

    @app.on_event("shutdown")
    async def shutdown() -> None:
        pipeline.stop()

    return app
