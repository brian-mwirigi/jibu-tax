"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.config import get_settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


settings = get_settings()

app = FastAPI(
    title="JibuTax Voice-First eTIMS API",
    description=(
        "Secure voice-first eTIMS orchestration "
        "for Kenya KRA compliance."
    ),
    docs_url=(
        "/docs"
        if settings.environment != "production"
        else None
    ),
    redoc_url=(
        "/redoc"
        if settings.environment != "production"
        else None
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, "cors_origins") and settings.cors_origins else (settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS else ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1",
)



@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}