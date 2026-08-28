from fastapi import APIRouter

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