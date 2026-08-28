"""
File: backend/app/main.py
Description:
    FastAPI Application Entry Point.
    - Instantiates the FastAPI application.
    - Configures CORS middleware for frontend communication.
    - Mounts all API v1 routes (/api/v1).
    - Manages application startup and shutdown lifecycle events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router

app = FastAPI(
    title="JibuTax Voice-First eTIMS API",
    version="1.0.0",
    description="Voice-First eTIMS Orchestrator for Kenya KRA compliance.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
