"""
File: backend/app/api/v1/api.py
Description:
    API Version 1 Router Aggregator.
    Aggregates sub-routers across all roles:
      - /agent: Role 4 LangGraph conversational agent invoke & checkpoint endpoints
      - /invoices: Role 3 eTIMS invoice generation & OSCU verification endpoints
      - /whatsapp: Role 3 WhatsApp receipt & QR code delivery endpoints
      - /kra: Role 1/3 KRA PIN verification endpoints
      - /tools: Role 2 ElevenLabs webhook tool endpoints
      - /ledger: Role 5 immutable ledger sales endpoints
      - /filings: Role 5 Turnover Tax & NIL return filing endpoints
      - /taxpayers: Role 3 phone-to-PIN taxpayer registration endpoints
"""

from fastapi import APIRouter
from app.api.v1 import (
    agent,
    invoices,
    whatsapp,
    kra,
    webhooks,
    ledger,
    filings,
    taxpayers,
    stats,
)

api_router = APIRouter()

api_router.include_router(agent.router)
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp"])
api_router.include_router(kra.router, prefix="/kra", tags=["KRA"])
api_router.include_router(webhooks.router, prefix="/tools", tags=["Tools"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Ledger"])
api_router.include_router(filings.router, prefix="/filings", tags=["Filings"])
api_router.include_router(taxpayers.router, prefix="/taxpayers", tags=["Taxpayers"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
