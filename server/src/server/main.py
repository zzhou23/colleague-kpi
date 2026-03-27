# server/src/server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from server.config import Settings
from server.api.deps import set_settings
from server.api.router import api_router
from server.db.models import Base


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()
    set_settings(settings)

    app = FastAPI(title="AI Performance Review", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    sync_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    return app
