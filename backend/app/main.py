"""FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.config import get_settings
from app.database import ensure_schema
from app.models import CallSession, Invoice, InvoiceItem, Taxpayer  # noqa: F401
from app.services.tax_engine import TaxValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema()
    yield


app = FastAPI(
    title="JibuTax eTIMS OSCU",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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


@app.get("/health")
def health():
    return {"ok": True, "service": "jibutax-oscu"}


app.include_router(api_router, prefix="/api/v1")
