import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.cases import router as cases_router
from app.api.legal import router as legal_router
from app.api.runs import router as runs_router

logging.basicConfig(level=logging.INFO)

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(cases_router)
    app.include_router(legal_router)
    app.include_router(runs_router)
    return app

app = create_app()