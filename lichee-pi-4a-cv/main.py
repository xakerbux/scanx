"""Точка входа."""

import argparse

import uvicorn

from cv_module.api.app import create_app
from cv_module.config import load_config
from cv_module.logging_setup import setup_logging


def main() -> None:
    p = argparse.ArgumentParser(description="CV Module SATK")
    p.add_argument("--config", default=None)
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--mock", action="store_true")
    args = p.parse_args()

    cfg = load_config(args.config)
    if args.mock:
        cfg.mock_inference = True
    if args.host:
        cfg.api_host = args.host
    if args.port:
        cfg.api_port = args.port

    setup_logging(cfg.logs_dir)
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port)


if __name__ == "__main__":
    main()
