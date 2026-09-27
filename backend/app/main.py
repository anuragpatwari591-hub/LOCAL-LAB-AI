"""LOCAL-LAB-AI backend entrypoint.

Binds to loopback only by default (see config/default.yaml `server.allow_remote`).
No telemetry, no analytics, no external network calls at runtime.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import routes_chat, routes_documents, routes_meta, routes_ocr
from .core import paths
from .core.config import get_config
from .engine.manager import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("local_lab_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths.ensure_data_dirs()
    cfg = get_config()
    engine = get_engine(cfg.llm)

    try:
        engine.start()
        healthy = engine.wait_until_healthy(timeout_s=90.0)
        if not healthy:
            logger.warning(
                "Inference engine did not report healthy within timeout. "
                "Chat requests will fail until it becomes available. "
                "Check logs/engine.log for details."
            )
    except Exception as exc:  # noqa: BLE001 - we want the API to still serve diagnostics
        logger.error("Failed to start inference engine: %s", exc)

    yield

    engine.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LOCAL-LAB-AI",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
    )

    app.include_router(routes_meta.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_documents.router)
    app.include_router(routes_ocr.router)

    frontend_dir = paths.FRONTEND_DIR / "static"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()
