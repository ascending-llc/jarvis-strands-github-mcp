"""FastAPI app factory and A2A gateway registration."""

from __future__ import annotations

from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.research import router as research_router
from agents.gateway import build_agent_apps
from agents.shared.core.logging_config import get_logger


logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AWS Customer Intelligence Orchestrator", version="0.1.0")
    app.include_router(health_router)
    app.include_router(research_router)

    for path, subapp in build_agent_apps().items():
        logger.info("Mounting A2A agent at %s", path)
        app.mount(path, subapp)

    return app
