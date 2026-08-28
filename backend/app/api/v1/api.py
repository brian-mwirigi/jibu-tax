"""
File: backend/app/api/v1/api.py
Description:
    API Version 1 Router Aggregator.
    Mounts all sub-routers from every team role into a single APIRouter.
"""

from fastapi import APIRouter
from app.api.v1 import agent, kra, webhooks, filings, ledger, taxpayers

api_router = APIRouter()

api_router.include_router(agent.router)
api_router.include_router(kra.router, prefix="/kra", tags=["KRA"])
api_router.include_router(webhooks.router, prefix="/tools", tags=["Tools"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Ledger"])
api_router.include_router(filings.router, prefix="/filings", tags=["Filings"])
api_router.include_router(taxpayers.router, prefix="/taxpayers", tags=["Taxpayers"])
