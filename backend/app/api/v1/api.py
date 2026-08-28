"""Version 1 router. Other roles mount their routes here later."""

from fastapi import APIRouter

from app.api.v1 import invoices, whatsapp

api_router = APIRouter()
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
