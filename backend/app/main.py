"""
File: backend/app/main.py
Description:
    FastAPI Application Entry Point.
    Initializes database schema, mounts API routers, configures CORS middleware,
    and registers global tax validation exception handlers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.config import get_settings
from app.database import init_db
from app.services.tax_engine import TaxValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="JibuTax Voice-First eTIMS API",
    version="1.0.0",
    description="Secure voice-first eTIMS orchestration for Kenya KRA compliance.",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, "cors_origins") and settings.cors_origins else ["*"],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TaxValidationError)
async def tax_error_handler(_request: Request, exc: TaxValidationError):
    return JSONResponse(
        status_code=400,
        content={"ok": False, "code": exc.code, "message": exc.message},
    )


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "jibutax-api"}


app.include_router(
    api_router,
    prefix="/api/v1",
)
