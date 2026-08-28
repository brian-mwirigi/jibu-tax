from fastapi import APIRouter
from app.api.v1.agent import router as agent_router
from app.api.v1 import filings, ledger, taxpayers

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(ledger.router, prefix="/ledger", tags=["ledger"])
api_router.include_router(filings.router, prefix="/filings", tags=["filings"])
api_router.include_router(taxpayers.router, prefix="/taxpayers", tags=["taxpayers"])

from app.api.v1 import agent, kra, webhooks


api_router = APIRouter()

api_router.include_router(agent.router)

api_router.include_router(
    kra.router,
    prefix="/kra",
    tags=["KRA"],
)

api_router.include_router(
    webhooks.router,
    prefix="/tools",
    tags=["Tools"],
)
